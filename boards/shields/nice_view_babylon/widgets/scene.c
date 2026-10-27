/*
 * Night picture while PC one (Bluetooth profile 1) is active, day picture
 * while PC two (profile 2) is active. Works on both halves: the left half
 * tells the right half which PC is active (see src/pc_scene.c).
 *
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zmk/display.h>
#include <zmk/event_manager.h>

#include "scene.h"

#if IS_ENABLED(CONFIG_ZMK_PC_SCENE)
#include <pc_scene.h>
#endif

#define PC_TWO_PROFILE 1 /* profiles count from 0: 0 = PC one, 1 = PC two */

struct scene_art {
    lv_obj_t *obj;
    const lv_img_dsc_t *day;
    const lv_img_dsc_t *night;
};

static struct scene_art arts[2];
static size_t art_count;

struct scene_state {
    uint8_t profile;
};

static void scene_update_cb(struct scene_state state) {
    for (size_t i = 0; i < art_count; i++) {
        lv_img_set_src(arts[i].obj,
                       state.profile == PC_TWO_PROFILE ? arts[i].day : arts[i].night);
    }
}

static struct scene_state scene_get_state(const zmk_event_t *eh) {
#if IS_ENABLED(CONFIG_ZMK_PC_SCENE)
    return (struct scene_state){.profile = zmk_pc_scene_profile()};
#else
    return (struct scene_state){.profile = 0};
#endif
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_scene, struct scene_state, scene_update_cb, scene_get_state)
#if IS_ENABLED(CONFIG_ZMK_PC_SCENE)
ZMK_SUBSCRIPTION(widget_scene, zmk_pc_scene_changed);
#endif

void scene_art_add(lv_obj_t *obj, const lv_img_dsc_t *day, const lv_img_dsc_t *night) {
    if (art_count < ARRAY_SIZE(arts)) {
        arts[art_count++] = (struct scene_art){.obj = obj, .day = day, .night = night};
    }
    widget_scene_init();
}
