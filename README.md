# butano auxiliary scripts

This repository contains scripts for use in [butano](https://github.com/GValiente/butano) projects.

## tilemap_minimizer.py

This script creates a minimized tilemap BMP file, a palette BMP file and a C++ header file containing map data, all to be used in a butano project. As a basis for this it needs both the original, generic tilemap graphics file and a tiled project file (.tmx). 

### How it works

- Iterate over all JSON files in /graphics which will represent the final tilemap
- For each JSON file that contains a 'tmx' value, use it locate the tiled TMX file
- Find the referenced TSX file and by that the original tilemap graphics file
- Compare each 8x8 pixel cluster in the graphics file to every other 8x8 pixel cluster and mark that cluster as either unique or reference a cluster with the exact same pixels, taking vertical and horizontal flipping into account
- Store all unique 8x8 pixel clusters into a minimized BMP file
- Iterate over all pixels and extract pixel color values, store these in a palette file and apply this palette to the minimized BMP file
- Iterate over all tiles in the tiled map and match the tile's location in the original tilemap with the location in the minimized location, taking vertical and horizontal flipping into account
- Store these informations into a C++ header file as a const struct

The generated tilemap should be automatically recognised by butano and converted in the build process. To then create a map with the tilemap and the generated struct, you can do something like this:

```C++
#include "tilemap_tiles.hpp"
#include "bn_regular_bg_tiles_items_tilemap_tiles.h"
#include "bn_bg_palette_items_tilemap_tiles_palette_1.h"

/////////////////////

bn::regular_bg_tiles_ptr tilemap = bn::regular_bg_tiles_items::tilemap_tiles.create_tiles();
bn::bg_palette_ptr palette = bn::bg_palette_items::tilemap_tiles_palette_1.create_palette();
bn::regular_bg_map_item bg_item(
    projectname::tilemaps::tilemap_tiles[0],
    bn::size(projectname::tilemaps::tilemap_tiles.width, 
             projectname::tilemaps::tilemap_tiles.height)
);
bn::regular_bg_map_ptr bg_map = bn::regular_bg_map_ptr::create(
    bg_item,
   	tilemap,
    palette
);
bn::regular_bg_ptr bg = bn::regular_bg_ptr::create(0,0,bg_map);
```

### Assumptions and limitations

This script assumes the following:

- It is run from the project's root folder (i.e. where the Makefile usually is)
- The required JSON file in /graphics for the tilemap image must exist and contain a "tmx" name-value-pair pointing to the tiled project file (.tmx), preferably located under /graphics/ressources
- There exists a ressources subfolder under /graphics where the .tmx, .tsx and original tilemap file is located
- The tiled project file is in CSV mode (i.e. the map data is comma-separated)

It has the following limitations:

- GBA maps must be multiples of 32\*8 pixels in each dimension (i.e. 32x32, 32x64, 64x96, etc.),so the tiled project needs to reflect that.
  - For example: If you are using 16x16 tilemaps, you must use 16x16, 16x32, 32x48, etc.
- It currently only supports 16x16 tilemaps (others could work but haven't been tested yet)

## How to set up in butano project

Simply clone this repository inside your butano project and reference it in your Makefile:

```Makefile
EXTTOOL     := @$(PYTHON) -B butano-auxiliary/tilemap_minimizer.py -n projectname
```

If you track your own project using git you might as well use git's submodule feature:

```Bash
$ git submodule add git@github.com:alex-dot/butano-auxiliary.git auxiliary
```

This additionally uses the path argument of the submodule feature so you can keep your project's folder names nice and clean. 