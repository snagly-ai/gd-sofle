/*
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <lvgl.h>

/* Show `night` on PC one and `day` on PC two in this image object, and keep
 * it updated when the PC changes. */
void scene_art_add(lv_obj_t *obj, const lv_img_dsc_t *day, const lv_img_dsc_t *night);
