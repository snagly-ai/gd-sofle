/*
 * Shares the active Bluetooth profile with both halves.
 *
 * Only the left (central) half knows which PC is active. Whenever that
 * changes, it invokes the &pc_scene behaviour with the profile number. The
 * behaviour is "global", so ZMK runs it on the left half and also sends it
 * over the split link to the right half - the same way &rgb_ug commands reach
 * both halves. On each half the behaviour raises zmk_pc_scene_changed, which
 * the nice!view screens listen to.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_behavior_pc_scene

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/logging/log.h>

#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/event_manager.h>

#include <pc_scene.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

ZMK_EVENT_IMPL(zmk_pc_scene_changed);

static atomic_t current_profile = ATOMIC_INIT(0);

uint8_t zmk_pc_scene_profile(void) { return (uint8_t)atomic_get(&current_profile); }

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

#define PC_SCENE_NODE DT_INST(0, DT_DRV_COMPAT)

/* The split link carries behaviour names of up to 8 characters. */
BUILD_ASSERT(sizeof(DEVICE_DT_NAME(PC_SCENE_NODE)) <= 9,
             "Keep the pc_scene behaviour node name to 8 characters or fewer");

/* ------------------------------------------------- behaviour (both halves) */

static int on_pc_scene_pressed(struct zmk_behavior_binding *binding,
                               struct zmk_behavior_binding_event event) {
    atomic_set(&current_profile, (atomic_val_t)binding->param1);
    raise_zmk_pc_scene_changed((struct zmk_pc_scene_changed){.profile = binding->param1});
    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_pc_scene_released(struct zmk_behavior_binding *binding,
                                struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api pc_scene_driver_api = {
    .binding_pressed = on_pc_scene_pressed,
    .binding_released = on_pc_scene_released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
};

BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &pc_scene_driver_api);

/* ------------------------------------------- sender (left / central half) */

#if IS_ENABLED(CONFIG_ZMK_BLE) &&                                                                  \
    (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

#include <zmk/ble.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/position_state_changed.h>

#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
#include <zephyr/bluetooth/conn.h>
#endif

#define RESYNC_DELAY_MS 3000

static uint8_t resends_left;

/* The colour commands run on their own small task, not ZMK's main one. If the
 * link to the right half is backed up, sending a command can wait for space;
 * on its own task that wait can never hold up keypresses. */
#define PC_SCENE_STACK_SIZE 1536
K_THREAD_STACK_DEFINE(pc_scene_stack, PC_SCENE_STACK_SIZE);
static struct k_work_q pc_scene_q;
static atomic_t pc_scene_q_started = ATOMIC_INIT(0);

static void pc_scene_schedule(struct k_work_delayable *work, k_timeout_t delay) {
    if (atomic_cas(&pc_scene_q_started, 0, 1)) {
        k_work_queue_start(&pc_scene_q, pc_scene_stack, K_THREAD_STACK_SIZEOF(pc_scene_stack),
                           K_LOWEST_APPLICATION_THREAD_PRIO, NULL);
    }
    k_work_reschedule_for_queue(&pc_scene_q, work, delay);
}

static void send_work_handler(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(send_work, send_work_handler);

static void send_work_handler(struct k_work *work) {
    struct zmk_behavior_binding binding = {
        .behavior_dev = DEVICE_DT_NAME(PC_SCENE_NODE),
        .param1 = zmk_ble_active_profile_index(),
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
        LOG_WRN("PC scene: sending profile failed (%d)", err);
    }

    /* Send once more a little later, in case the right half was still
     * setting up its side of the link the first time. */
    if (resends_left > 0) {
        resends_left--;
        pc_scene_schedule(&send_work, K_MSEC(RESYNC_DELAY_MS));
    }
}

static void schedule_resync(void) {
    resends_left = 1;
    pc_scene_schedule(&send_work, K_MSEC(RESYNC_DELAY_MS));
}

static int pc_scene_listener(const zmk_event_t *eh) {
    if (as_zmk_ble_active_profile_changed(eh) != NULL) {
        pc_scene_schedule(&send_work, K_MSEC(10));
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(pc_scene, pc_scene_listener);
ZMK_SUBSCRIPTION(pc_scene, zmk_ble_active_profile_changed);

#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
/* A connection in the central role is the right half (re)connecting. */
static void pc_scene_connected(struct bt_conn *conn, uint8_t err) {
    struct bt_conn_info info;

    if (err || bt_conn_get_info(conn, &info) < 0 || info.role != BT_CONN_ROLE_CENTRAL) {
        return;
    }

    schedule_resync();
}

BT_CONN_CB_DEFINE(pc_scene_conn_callbacks) = {
    .connected = pc_scene_connected,
};
#endif

static int pc_scene_init(void) {
    schedule_resync();
    return 0;
}

SYS_INIT(pc_scene_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

#endif /* central */

#endif /* DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT) */
