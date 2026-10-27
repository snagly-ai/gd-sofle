/*
 * Which PC (Bluetooth profile) is active, shared with both halves so each
 * screen can show the matching picture: night for PC one, day for PC two.
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <zmk/event_manager.h>

/* Raised on both halves whenever the active Bluetooth profile is (re)sent. */
struct zmk_pc_scene_changed {
    uint8_t profile;
};

ZMK_EVENT_DECLARE(zmk_pc_scene_changed);

/* Last profile received on this half (0 = PC one until told otherwise). */
uint8_t zmk_pc_scene_profile(void);
