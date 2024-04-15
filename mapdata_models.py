#!/usr/bin/env python

"""mapdata_models.py: Defines map models to be used in the generation of butano-compatible
                      source files."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from PIL import Image

import config

@dataclass
class TilemapImageObject:
    '''Python representation of a tilemap image.'''
    name: str
    rows: int
    columns: int
    original: Image
    min_width: int
    min_height: int
    min_rgb: Image = None

@dataclass
class MapObject:
    '''Python representation of a map.'''
    # pylint: disable=too-many-instance-attributes
    name: str = ""
    width: int = 0
    height: int = 0
    bitmap: Image = None   # image data of tilemap
    bitmap_width: int = 0    # width of tileset bitmap in tiles
    bitmap_filename: str = ""
    columns: int = 0
    tilesize_factor: int = 0 # 1=8px, 2=16px, 4=32px, etc.
    tiles: dict = None           # dict of which tiles are used how
    tmx_filepath: str = ""
    xml: ET.Element = None
    map_layers: ET.Element = None      # XML data from tiled map file
    boundaries: list = None
    spawn_points: list = None
    gateways: list = None
    objects: list = None         # list of interactable objects (aka actors)
    npcs: list = None            # list of NPCs (aka characters)
    walk_cycles: list = None       # list of walk_cycles
    tilelist: str = ""   # flat tile data for C(++) object file

    def init(self,mapdict):
        '''Initialises using a mapdict from tilemap_compressor.'''
        # need to import here to prevent circular import
        from tilemap_compressor import create_tilemap # pylint: disable=import-outside-toplevel
        self.name = mapdict['map_name']
        self.width = int(mapdict['map_width']*(mapdict['map_tilesize']/8))
        self.height = int(mapdict['map_height']*(mapdict['map_tilesize']/8))
        self.bitmap_filename = mapdict['map_name']
        self.tmx_filepath = mapdict['tilemap_tmx_path']
        self.xml = mapdict['tilemap_xml']
        if config.PREVENT_MAP_CONSOLIDATION or not mapdict["combined_tilemap"]:
            bitmap,tilemap_width,_ = create_tilemap(mapdict)
            self.bitmap = bitmap
            self.columns = tilemap_width
            self.tiles = mapdict["images"]
        else:
            self.bitmap_filename = mapdict["combined_tilemap"]["mapdict"]["map_name"]
            self.bitmap = mapdict["combined_tilemap"]["bitmap"]
            self.columns = mapdict["combined_tilemap"]["tilemap_width"]
            self.tiles = mapdict["combined_tilemap"]["mapdict"]["images"]
            print("Skipping generation of tileset \""+self.name+\
                  "\" since it is included in: "+self.bitmap_filename)
        self.bitmap_width = int((self.columns*8)/mapdict['map_tilesize'])
        self.tilesize_factor = int(mapdict['map_tilesize']/8)
        self.map_layers = self.xml.findall("layer")

    def name_lower(self):
        '''Returns the map name in all lower case.'''
        return self.name.split(".",maxsplit=1)[0].lower()
    def name_upper(self):
        '''Returns the map name in all upper case.'''
        return self.name.split(".",maxsplit=1)[0].upper()
