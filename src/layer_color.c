/*
 * Layer colours for the RGB underglow.
 *
 * Runs on the central (left) half. Whenever the active layer or Bluetooth
 * profile changes it sends the colour configured for that layer and profile
 * (PC one / PC two) through the stock &rgb_ug behaviour.
 * &rgb_ug is a global behaviour, so the right half receives the same commands
 * over the split link and both halves stay in step.
 *
 * Configure colours with a "zmk,layer-color" node in the keymap.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_layer_color

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/logging/log.h>

#include <zmk/behavior.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/keymap.h>
#include <zmk/rgb_underglow.h>
#include <dt-bindings/zmk/rgb.h>

#if IS_ENABLED(CONFIG_ZMK_BLE)
#include <zmk/ble.h>
#include <zmk/events/ble_active_profile_changed.h>
#endif

#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
#include <zephyr/bluetooth/conn.h>
#endif

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

BUILD_ASSERT(DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT),
             "Layer colours need a zmk,layer-color node in the keymap");
BUILD_ASSERT(DT_NODE_EXISTS(DT_NODELABEL(rgb_ug)),
             "Layer colours need the &rgb_ug behaviour (CONFIG_ZMK_RGB_UNDERGLOW=y)");

#define RGB_UG_DEV DEVICE_DT_NAME(DT_NODELABEL(rgb_ug))

#define LAYER_COLOR_MAX_PROFILES 5

struct layer_color {
    uint8_t layer;
    uint16_t hues[LAYER_COLOR_MAX_PROFILES]; /* one per Bluetooth profile */
    uint8_t hue_count;
    uint8_t sat;
    int16_t brt; /* -1 keeps the brightness set with the RGB keys */
    uint8_t effect;
};

#define LAYER_COLOR_ENTRY(node)                                                                    \
    {                                                                                              \
        .layer = DT_PROP(node, layer),                                                             \
        .hues = DT_PROP(node, hue),                                                                \
        .hue_count = DT_PROP_LEN(node, hue),                                                       \
        .sat = DT_PROP(node, saturation),                                                          \
        .brt = DT_PROP_OR(node, brightness, -1),                                                   \
        .effect = DT_PROP(node, effect),                                                           \
    },

static const struct layer_color layer_colors[] = {DT_INST_FOREACH_CHILD(0, LAYER_COLOR_ENTRY)};

static const struct layer_color *last_applied;
static uint16_t last_hue;
static int16_t last_effect = -1;

/* The colour commands run on their own small task, not ZMK's main one. If the
 * link to the right half is backed up, sending a command can wait for space;
 * on its own task that wait can never hold up keypresses. */
#define LAYER_COLOR_STACK_SIZE 1536
K_THREAD_STACK_DEFINE(layer_color_stack, LAYER_COLOR_STACK_SIZE);
static struct k_work_q layer_color_q;
static atomic_t layer_color_q_started = ATOMIC_INIT(0);

static void layer_color_schedule(struct k_work_delayable *work, k_timeout_t delay) {
    if (atomic_cas(&layer_color_q_started, 0, 1)) {
        k_work_queue_start(&layer_color_q, layer_color_stack, K_THREAD_STACK_SIZEOF(layer_color_stack),
                           K_LOWEST_APPLICATION_THREAD_PRIO, NULL);
    }
    k_work_reschedule_for_queue(&layer_color_q, work, delay);
}
static bool force_apply;
static uint8_t resync_left;

/* Highest active layer that has a colour; falls back to lower active layers. */
static const struct layer_color *find_color(void) {
    for (int idx = ZMK_KEYMAP_LAYERS_LEN - 1; idx >= 0; idx--) {
        zmk_keymap_layer_id_t id = zmk_keymap_layer_index_to_id(idx);

        if (id == ZMK_KEYMAP_LAYER_ID_INVAL || !zmk_keymap_layer_active(id)) {
            continue;
        }

        for (size_t i = 0; i < ARRAY_SIZE(layer_colors); i++) {
            if (layer_colors[i].layer == idx) {
                return &layer_colors[i];
            }
        }
    }

    return NULL;
}

/* Hue for the active Bluetooth profile: first value = PC one, second = PC two. */
static uint16_t hue_for_profile(const struct layer_color *color) {
    int profile = 0;
#if IS_ENABLED(CONFIG_ZMK_BLE)
    profile = zmk_ble_active_profile_index();
#endif
    if (profile < 0 || profile >= color->hue_count) {
        profile = 0;
    }
    return color->hues[profile];
}

static void send_rgb_command(uint32_t cmd, uint32_t value) {
    struct zmk_behavior_binding binding = {
        .behavior_dev = RGB_UG_DEV,
        .param1 = cmd,
        .param2 = value,
    };
    struct zmk_behavior_binding_event event = {
        .layer = 0,
        .position = 0,
        .timestamp = k_uptime_get(),
#if IS_ENABLED(CONFIG_ZMK_SPLIT)
        .source = ZMK_POSITION_STATE_CHANGE_SOURCE_LOCAL,
#endif
    };

    int err = zmk_behavior_invoke_binding(&binding, event, true);
    if (err < 0) {
        LOG_WRN("Layer colour: RGB command %d failed (%d)", (int)cmd, err);
    }
}

static void apply_work_handler(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(apply_work, apply_work_handler);

static void apply_work_handler(struct k_work *work) {
    const struct layer_color *color = find_color();

    uint16_t hue = color != NULL ? hue_for_profile(color) : 0;

    if (color != NULL && (color != last_applied || hue != last_hue || force_apply)) {
        uint8_t brt = color->brt >= 0 ? (uint8_t)color->brt : zmk_rgb_underglow_calc_brt(0).b;

        /* Only send what changed: the effect rarely does, so usually this is
         * one command per colour change instead of two. */
        if (color->effect != last_effect || force_apply) {
            send_rgb_command(RGB_EFS_CMD, color->effect);
            last_effect = color->effect;
        }
        send_rgb_command(RGB_COLOR_HSB_CMD, RGB_COLOR_HSB_VAL(hue, color->sat, brt));

        last_applied = color;
        last_hue = hue;
    }

    force_apply = false;

    /* After the other half connects, send the colour again a little later in
     * case the split link was not ready to carry commands the first time. */
    if (resync_left > 0) {
        resync_left--;
        force_apply = true;
        layer_color_schedule(&apply_work, K_MSEC(CONFIG_ZMK_LAYER_COLOR_RESYNC_DELAY_MS));
    }
}

static void schedule_resync(void) {
    force_apply = true;
    resync_left = 1;
    layer_color_schedule(&apply_work, K_MSEC(CONFIG_ZMK_LAYER_COLOR_RESYNC_DELAY_MS));
}

static int layer_color_listener(const zmk_event_t *eh) {
    /* Layer changes, and switching PC (Bluetooth profile), both recolour. */
    layer_color_schedule(&apply_work, K_MSEC(CONFIG_ZMK_LAYER_COLOR_DEBOUNCE_MS));
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(layer_color, layer_color_listener);
ZMK_SUBSCRIPTION(layer_color, zmk_layer_state_changed);
#if IS_ENABLED(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(layer_color, zmk_ble_active_profile_changed);
#endif

#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
/* The left half is "central" only towards the right half, so a connection in
 * the central role means the right half has (re)connected. */
static void layer_color_connected(struct bt_conn *conn, uint8_t err) {
    struct bt_conn_info info;

    if (err || bt_conn_get_info(conn, &info) < 0 || info.role != BT_CONN_ROLE_CENTRAL) {
        return;
    }

    schedule_resync();
}

BT_CONN_CB_DEFINE(layer_color_conn_callbacks) = {
    .connected = layer_color_connected,
};
#endif

static int layer_color_init(void) {
    schedule_resync();
    return 0;
}

SYS_INIT(layer_color_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
