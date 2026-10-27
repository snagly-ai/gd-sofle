zephyr_include_directories(include)

if(CONFIG_ZMK_LAYER_COLOR)
  target_sources(app PRIVATE src/layer_color.c)
endif()

if(CONFIG_ZMK_PC_SCENE)
  target_sources(app PRIVATE src/pc_scene.c)
endif()
