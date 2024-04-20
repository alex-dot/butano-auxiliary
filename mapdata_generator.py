#!/usr/bin/env python
# pylint: disable=invalid-name

"""mapdata_generator.py: Generate butano-compatible map headers from tiled projects."""

import os
import sys
import json
import math
import argparse
import datetime

import config
import tilemap_compressor as tc
import tilemap_minimizer as tm
from mapdata_models import MapObject

def calculate_movement_speed(origin,destination,pps,speed_factor=1.0):
    '''Calculates movements speed for characters, so that they move uniformly across the map.
       pps: pixel per second'''
    distance = math.sqrt(((origin[0]-destination[0])**2)+((origin[1]-destination[1])**2))
    speed = int(distance/float(pps) * speed_factor)
    return speed

def write_tilemap_globals_file():
    '''Creates a header file defining map data structs to be used by tilemaps.'''
    # pylint: disable=too-many-statements

    with open("include/globals_tilemaps.hpp","w",encoding='UTF-8') as hpp:
        hpp.write("/*\n")
        hpp.write(" * "+config.FILE_HEADER+"\n")
        hpp.write(" *\n")
        hpp.write(" * Copyright (c) "+str(datetime.date.today().year)+" "+config.AUTHOR_NAME+\
                  " "+config.AUTHOR_MAIL+"\n")
        hpp.write(" *\n")
        hpp.write(" * Defines tilemap struct template as used in map header files. \n")
        hpp.write(" */\n\n")
        hpp.write("#ifndef "+config.NAMESPACE_UNDERSCORE.upper()+"GLOBALS_TILEMAPS_HPP\n")
        hpp.write("#define "+config.NAMESPACE_UNDERSCORE.upper()+"GLOBALS_TILEMAPS_HPP\n\n")
        if config.NAMESPACE:
            hpp.write("namespace "+config.NAMESPACE_COLON.lower()+"tilemaps {\n\n")
        else:
            hpp.write("namespace tilemaps {\n\n")

        hpp.write("    template<uint16_t width_, uint16_t height_>\n")
        hpp.write("    struct tm_t {\n")
        hpp.write("        uint16_t base[width_*height_];\n")
        hpp.write("        uint16_t props[width_*height_];\n")
        hpp.write("        uint16_t cover[width_*height_];\n")
        hpp.write("        uint16_t width = width_;\n")
        hpp.write("        uint16_t height = height_;\n")
        hpp.write("    };\n\n")

        if config.PARSE_ACTORS:
            hpp.write("    struct spawn_point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("        uint8_t direction;\n")
            hpp.write("        bool    dflt;\n")
            hpp.write("        char    name[6];\n")
            hpp.write("    };\n")
        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    struct point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("    };\n")
            hpp.write("    struct polygon_t {\n")
            hpp.write("        point_t point;\n")
            hpp.write("    };\n")
            hpp.write("    struct boundary_metadata_t {\n")
            hpp.write("        uint32_t number_of_points;\n")
            hpp.write("        uint16_t min_x;\n")
            hpp.write("        uint16_t max_x;\n")
            hpp.write("        uint16_t min_y;\n")
            hpp.write("        uint16_t max_y;\n")
            hpp.write("        char map_name[9];\n")
            hpp.write("        char spawn_point_name[6];\n")
            hpp.write("    };\n")
        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    struct metadata_t {\n")
            hpp.write("        uint8_t number_of_spawn_points;\n")
            hpp.write("        uint8_t number_of_boundaries;\n")
            hpp.write("        uint8_t number_of_gateways;\n")
            hpp.write("    };\n\n")

        hpp.write("}\n\n")
        hpp.write("#endif\n\n")

def write_tilemap_header_file(Map):
    '''Creates a header file defining GBA compatible map data, like tilemap or objects.'''
    with open("include/" + Map.bitmap_filename.split(".")[0] + ".hpp","w",encoding='UTF-8') as hpp:
        hpp.write("/*\n")
        hpp.write(" * "+config.FILE_HEADER+"\n")
        hpp.write(" *\n")
        hpp.write(" * Copyright (c) "+str(datetime.date.today().year)+" "+config.AUTHOR_NAME+\
                  " "+config.AUTHOR_MAIL+"\n")
        hpp.write(" *\n")
        hpp.write(" * Map data for map "+Map.name+". \n")
        hpp.write(" */\n\n")
        hpp.write("#ifndef " + config.NAMESPACE_UNDERSCORE.upper() + Map.name_upper() + "_HPP\n")
        hpp.write("#define " + config.NAMESPACE_UNDERSCORE.upper() + Map.name_upper() + "_HPP\n\n")
        hpp.write("#include \"bn_regular_bg_tiles_item.h\"\n")
        hpp.write("#include \"bn_bg_palette_item.h\"\n\n")
        hpp.write("#include \"globals.hpp\"\n")
        hpp.write("namespace "+config.NAMESPACE_COLON.lower()+"tilemaps::"+Map.name_lower()+" {\n")

        hpp.write("    extern const bn::regular_bg_tiles_item* bg_tiles;\n")
        hpp.write("    extern const bn::bg_palette_item*       bg_palette;\n")
        hpp.write("    extern const tm_t<"+str(Map.width)+","+str(Map.height)+"> tilemap;\n")

        if config.PARSE_ACTORS:
            for spawn_point in Map.spawn_points:
                hpp.write("    extern const spawn_point_t "+\
                          "spawn_point_"+spawn_point.get("name")+";\n")
            hpp.write("    extern const spawn_point_t "+\
                      "spawn_points["+str(len(Map.spawn_points))+"];\n")

        if config.PARSE_ACTORS:
            number_of_points = [x['number_of_points'] for x in Map.gateways]
            hpp.write("    extern const polygon_t gateways["+str(sum(number_of_points)*2)+"];\n")
            hpp.write("    extern const boundary_metadata_t "+\
                      "gateway_metadata["+str(len(Map.gateways))+"];\n")

        if config.PARSE_BOUNDARIES:
            number_of_points = [x['number_of_points'] for x in Map.boundaries]
            hpp.write("    extern const polygon_t boundaries["+str(sum(number_of_points)*2)+"];\n")
            hpp.write("    extern const boundary_metadata_t "+\
                      "boundary_metadata["+str(len(Map.boundaries))+"];\n")

        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    extern const metadata_t metadata;\n")

        hpp.write("\n}\n\n")

        hpp.write("namespace "+config.NAMESPACE_COLON.lower()+"actors::"+Map.name_lower()+" {\n")
        hpp.write("    extern const character_t* characters;\n")
        hpp.write("    extern const container_t* containers;\n")
        hpp.write("    alignas(int) extern const metadata_t metadata;\n")

        hpp.write("\n}\n\n#endif\n")

def write_tilemap_data(Map, cpp):
    '''Writes the tilemap data, i.e. which tile to render where.'''
    cpp.write("    const tm_t<"+str(Map.width)+","+str(Map.height)+"> tilemap = {\n")
    cpp.write(Map.tilelist)
    cpp.write("        " + str(Map.width)  + ", // width\n")
    cpp.write("        " + str(Map.height) + "  // height\n")
    cpp.write("\n    };\n")

def write_boundary_data(boundary_data, typename, cpp):
    '''Writes data for boundaries on a map that curtails the player.'''
    if typename == "boundaries":
        typename_plural = "boundaries"
        typename_singular = "boundary"
    elif typename == "gateways":
        typename_plural = "gateways"
        typename_singular = "gateway"
    else:
        raise ValueError("Unsupported typename of boundary data found: "+typename)

    number_of_points = [x['number_of_points'] for x in boundary_data]
    cpp.write("    const polygon_t "+typename_plural+"["+str(sum(number_of_points)*2)+"] = {\n")

    for boundary in boundary_data:
        for point in boundary['points']:
            cpp.write("        "+point['x']+","+point['y']+",\n")

    cpp.write("    };\n")

    cpp.write("\n    const boundary_metadata_t "+typename_singular+\
              "_metadata["+str(len(boundary_data))+"] {\n")
    for boundary in boundary_data:
        cpp.write("        "+str(boundary['number_of_points'])+",")
        cpp.write(str(boundary['min_x'])+",")
        cpp.write(str(boundary['max_x'])+",")
        cpp.write(str(boundary['min_y'])+",")
        cpp.write(str(boundary['max_y'])+",")
        if typename == "boundaries":
            cpp.write("\"\",\"\",\n")
        elif typename == "gateways":
            cpp.write("\""+boundary['map_name']+"\",")
            cpp.write("\""+boundary['spawn_point_name'][:5]+"\",\n")
    cpp.write("    };\n\n")

def write_spawnpoint_data(spawn_point_data, cpp):
    '''Writes data for spawnpoints.'''
    for spawn_point in spawn_point_data:
        name = spawn_point.get("name")
        if len(name) > 5:
            print("Warning: Name of spawn_point ("+name+") too long, contracted to: "+name[:5])

        cpp.write("    const spawn_point_t spawn_point_"+name+" = {\n")
        cpp.write("        "+str(int(float(spawn_point.get("x"))))+",\n")
        cpp.write("        "+str(int(float(spawn_point.get("y"))))+",\n")

        face_direction, default_spawn_point = None, None
        for prop in spawn_point.find("properties").findall("property"):
            if prop.get("name") == "default":
                default_spawn_point = prop.get("value")
            if prop.get("name") == "face_direction":
                face_direction = prop.get("value")

        if face_direction == "up":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_UP,\n")
        elif face_direction == "down":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_DOWN,\n")
        elif face_direction == "left":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_LEFT,\n")
        elif face_direction == "right":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_RIGHT,\n")
        else:
            raise ValueError("In spawn_point construction: Invalid face direction found: " + name)

        cpp.write("        "+default_spawn_point+",\n")

        cpp.write("        \""+name[0:5]+"\"\n")
        cpp.write("    };\n")

    cpp.write("    const spawn_point_t spawn_points["+str(len(spawn_point_data))+"] = {\n")
    for spawn_point in spawn_point_data:
        cpp.write("        spawn_point_"+spawn_point.get("name")+",\n")
    cpp.write("    };\n\n")

def collect_walk_cycle_data(Map):
    '''Collects data for walk_cycles'''
    walk_cycle_data = []
    for wc in Map.walk_cycles:
        walk_cycle_origin = (float(wc.get("x")),float(wc.get("y")))
        npc_id = None
        idle_anims = {0:"{0,0}"}
        pauses = {0:"60"}
        for prop in wc.find("properties").findall("property"):
            if prop.get("name") == "character":
                npc_id = prop.get("value")
            if prop.get("name") == "pause":
                pauses[0] = prop.get("value")
            if prop.get("name") == "idle_anim":
                idle_anims[0] = prop.get("value")

            for i in range(len(wc.find("polygon").get("points").split(" "))):
                if prop.get("name") == str("pause_"+str(i)):
                    pauses[i] = prop.get("value")
                if prop.get("name") == str("idle_anim_"+str(i)):
                    idle_anims[i] = prop.get("value")

        npc_name = None
        for npc in Map.npcs:
            if npc.get("id") == npc_id:
                npc_name = npc.get("name")

        if not npc_name:
            raise ValueError("Could not determine NPC for walk_cycle: "+wc.get("name"))

        movements = []
        for i,point in enumerate(wc.find("polygon").get("points").split(" ")):
            x = int(float(point.split(",")[0])+walk_cycle_origin[0])
            y = int(float(point.split(",")[1])+walk_cycle_origin[1])
            movement_pause = pauses[0] if i+1 not in pauses else pauses[i+1]
            movement_idle_anim = None if i+1 not in idle_anims else idle_anims[i+1]
            movement = {
                "x": x,
                "y": y,
                "speed": 16,
                "pause": movement_pause,
                "idle_anim": movement_idle_anim
            }
            movements.append(movement)

        for i,mm in enumerate(movements):
            origin = [mm["x"],mm["y"]]
            destination = [movements[i+1]["x"],movements[i+1]["y"]] if i<len(movements)-2\
                else [movements[0]["x"],movements[0]["y"]]
            movements[i]["speed"] = str(calculate_movement_speed(origin,destination,1))

        walk_cycle_data.append({
                "name": npc_name+"_walk_cycle",
                "hero_name": npc_name,
                "movements": movements,
                "idle_anim": idle_anims[0],
                "pause": pauses[0]
            })

    return walk_cycle_data

def write_walk_cycle_data(Map, cpp):
    '''Writes data for walk_cycles'''
    walk_cycle_data = collect_walk_cycle_data(Map)
    
    for wc in walk_cycle_data:
        for i,mm in enumerate(wc["movements"]):
            cpp.write("    const movement_t "+wc["hero_name"]+"_wc_m_"+str(i)+" = {\n")
            cpp.write("        "+str(mm["x"])+","+str(mm["y"])+",\n")
            cpp.write("        "+mm["pause"]+",\n")
            cpp.write("        "+mm["speed"])
            if mm["idle_anim"]:
                cpp.write(",\n        "+mm["idle_anim"])
            cpp.write("\n    };\n")

        cpp.write("    const walk_cycle_t "+wc["name"]+" = {\n")
        cpp.write("        "+str(len(wc["movements"]))+",\n")
        cpp.write("        {")
        for i,mm in enumerate(wc["movements"]):
            cpp.write("&"+wc["hero_name"]+"_wc_m_"+str(i))
            if i < len(wc["movements"])-1:
                cpp.write(",")
        cpp.write("}\n")
        cpp.write("    };\n")

    cpp.write("\n")

    return len(walk_cycle_data)

def write_npc_data(Map, cpp):
    '''Writes data for NPCs'''
    npc_data = []
    for npc in Map.npcs:
        face_direction,blurb,walk_cycle,idle_animation = None,None,None,None
        for prop in npc.find("properties").findall("property"):
            if prop.get("name") == "face_direction":
                face_direction = prop.get("value")
            if prop.get("name") == "blurb":
                blurb = prop.get("value")
            if prop.get("name") == "idle_animation":
                idle_animation = prop.get("value")
            if prop.get("name") == "walk_cycle":
                walk_cycle = True

        cpp.write("    const character_t "+npc.get("name")+ " = {\n")
        cpp.write("        \""+npc.get("name")+"\",\n")

        if face_direction == "up":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_UP,\n")
        elif face_direction == "down":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_DOWN,\n")
        elif face_direction == "left":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_LEFT,\n")
        elif face_direction == "right":
            cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_RIGHT,\n")
        else:
            raise ValueError("In character construction: Invalid face direction found for: " + npc.get("name"))

        cpp.write("        "+str(int(float(npc.get("x"))))+","+str(int(float(npc.get("y"))))+",\n")

        if blurb:
            cpp.write("        &"+config.NAMESPACE_COLON.lower()+"texts::"+Map.name+"::"+npc.get("name")+"_blurb,\n")
        else:
            cpp.write("        nullptr,\n")
        if idle_animation:
            cpp.write("        "+idle_animation+",\n")
        else:
            cpp.write("        {0,0},\n")
        if walk_cycle:
            cpp.write("        &"+npc.get("name")+"_walk_cycle\n")
        else:
            cpp.write("        nullptr\n")

        cpp.write("    };\n")
        npc_data.append({'name':npc.get("name")})

    cpp.write("    const character_t* characters = {\n")
    for npc in npc_data:
        cpp.write("        &"+npc['name']+"\n")
    cpp.write("    };\n\n")

    return len(npc_data)

def write_container_data(Map, cpp):
    '''Writes data for interactable containers.'''
    item_data = ["","potion"]
    chest_data = []
    for actors in Map.objects:
        cpp.write("    const container_t "+actors.get("name")+" = {\n")
        for prop in actors.find("properties").findall("property"):
            if prop.get("name") == "contains":
                for item in prop.get("value").split(")"):
                    if item:
                        item_name = item_data[int(item.split(",")[0][1:])]
                        item_count = item.split(",")[1]
                        cpp.write("        \""+item_name+"\","+item_count+",\n")
        tlx = str(int(float(actors.get("x"))))
        tly = str(int(float(actors.get("y")))-int(float(actors.get("height"))))
        brx = str(int(float(actors.get("x")))+int(float(actors.get("width"))))
        bry = str(int(float(actors.get("y"))))
        cpp.write("        "+tlx+","+tly+",\n")
        cpp.write("        "+brx+","+bry+"\n")
        cpp.write("    };\n")
        chest_data.append({'name':actors.get("name")})

    cpp.write("    const container_t* containers = {\n")
    for chest in chest_data:
        cpp.write("        &"+chest['name']+"\n")
    cpp.write("    };\n\n")

    return len(chest_data)

def write_actor_data(Map, cpp):
    '''Writes data for interactable objects, like NPCs and containers.'''
    num_walk_cycles = write_walk_cycle_data(Map, cpp)
    num_npcs = write_npc_data(Map, cpp)
    num_containers = write_container_data(Map, cpp)

    cpp.write("    const metadata_t metadata = {\n")
    cpp.write("        ")
    cpp.write(str(num_containers)+",")
    cpp.write(str(num_npcs)+",")
    cpp.write(str(num_walk_cycles)+"\n")
    cpp.write("    };\n")

def write_object_data(Map, cpp):
    '''Conditionally calls other object write functions and closes with metadata info.'''
    if Map.boundaries:
        write_boundary_data(Map.boundaries, "boundaries", cpp)
    else:
        print("Warning: No boundary data found, characters will be able to walk anywhere.")
        write_boundary_data([], "boundaries", cpp)

    if Map.gateways:
        write_boundary_data(Map.gateways, "gateways", cpp)
    else:
        print("Warning: No gateway data found, map must be loaded manually.")
        write_boundary_data([], "gateways", cpp)

    if Map.spawn_points:
        write_spawnpoint_data(Map.spawn_points, cpp)
    else:
        print("Warning: No spawnpoint data found, characters will be spawned at 0,0.")
        write_spawnpoint_data([], cpp)

    cpp.write("    const metadata_t metadata = {\n")
    cpp.write("        uint8_t("+str(len(Map.spawn_points))+"),\n")      # spawn_point count
    cpp.write("        uint8_t("+str(len(Map.boundaries))+"),\n")        # boundary count
    cpp.write("        uint8_t("+str(len(Map.gateways))+")\n")           # gateway count
    cpp.write("    };\n\n")


def write_tilemap_cpp_file(Map):
    '''Base function creating the map code file, conditionally writing object or text data.'''
    with open("src/" + Map.name_lower() + ".cpp","w",encoding='UTF-8') as cpp:
        cpp.write("#include \""+Map.name_lower()+".hpp\"\n\n")

        cpp.write("#include \"bn_regular_bg_tiles_items_"+Map.bitmap_filename+".h\"\n")
        cpp.write("#include \"bn_bg_palette_items_"+Map.bitmap_filename+"_palette.h\"\n\n")

        # TODO requires proper handling
        cpp.write("namespace " + config.NAMESPACE_COLON.lower() +\
                  "texts::"+Map.name_lower()+" {\n")
        cpp.write("    const text_t text = \"Crono received 1 potion.\";\n")
        cpp.write("    const text_t hero_blurb = \"FIX ME, PLZ!\";\n")
        cpp.write("}\n\n")

        # TODO requires proper handling
        cpp.write("namespace " + config.NAMESPACE_COLON.lower() +\
                  "actors::"+Map.name_lower()+" {\n")
        if (config.PARSE_ACTORS):
            write_actor_data(Map,cpp)
        cpp.write("}\n\n")

        cpp.write("namespace " + config.NAMESPACE_COLON.lower() +\
                  "tilemaps::"+Map.name_lower()+" {\n")

        cpp.write("    const bn::regular_bg_tiles_item* bg_tiles   = "+\
                  "&bn::regular_bg_tiles_items::"+Map.bitmap_filename+";\n")
        cpp.write("    const bn::bg_palette_item*       bg_palette = "+\
                  "&bn::bg_palette_items::"+Map.bitmap_filename+"_palette;\n")

        write_tilemap_data(Map, cpp)

        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            write_object_data(Map, cpp)

        cpp.write("}\n")

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate butano-compatible map headers from tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-map-gen',dest='force_map',action='store_true',
                           help='Force tilemap data generation')
    argparser.add_argument('-s','--save-temp-files',dest='save_temp_imgs',action='store_true',
                           help="""Save temporary files (like *_minimized.bmp and *_combined.bmp
                                   and some json files)""")
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring foton.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring foton.json; requires --map-file')
    argparser.add_argument('--no-minimization',dest='prevent_minimization',action='store_true',
                           help='Do not minimize tilemap before compression')
    argparser.add_argument('--no-map-consolidation',
                           dest='prevent_consolidation',action='store_true',
                           help="""Prevent consolidation of maps so each map will have their own
                                   generated tilemap""")
    argparser.add_argument('-n','--namespace',dest='namespace',
                           help='Set namespace for project')
    argparser.add_argument('-o','--create-objects',dest='objects',action='store_true',
                           help='Parse all object layers (actors and boundaries)')
    argparser.add_argument('--create-actors',dest='actors',action='store_true',
                           help='Parse actor layer')
    argparser.add_argument('--create-boundaries',dest='boundaries',action='store_true',
                           help='Parse boundary layer')
    argparser.add_argument('-g','--globals',dest="globals",action='store_true',
                           help='Create globals file')
    argparser.add_argument('-a','--author',dest='author_name',
                           help='Author name to be put into copyright line.')
    argparser.add_argument('-m','--mail',dest='author_mail',
                           help='Author mail address to be put into copyright line.')
    argparser.add_argument('--header-line',dest='header_line',
                           help='Author name to be put into copyright line.')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_MAP_DATA_GENERATION = True
    if args.force_map:
        config.FORCE_MAP_DATA_GENERATION = True
    if args.save_temp_imgs:
        config.SAVE_TEMPORARY_FILES = True
    if ( args.tmx_override and not args.map_name ) or \
       ( not args.tmx_override and args.map_name ):
        print("If either --map-file or --map-name is set, the other must be set, too")
        sys.exit()
    if args.tmx_override:
        config.TMX_OVERRIDE = args.tmx_override.split('/')[-1]
        if not os.path.exists("graphics/ressources/" + config.TMX_OVERRIDE):
            print("Did not find a tiled map file: "+config.TMX_OVERRIDE)
            sys.exit()
    if args.map_name:
        config.MAP_NAME = args.map_name
    if args.prevent_minimization:
        config.PREVENT_TILEMAP_MINIMIZATION = True
    if args.prevent_consolidation:
        config.PREVENT_MAP_CONSOLIDATION = True
    if args.namespace:
        config.NAMESPACE = args.namespace
        config.NAMESPACE_UNDERSCORE = config.NAMESPACE + "_"
        config.NAMESPACE_COLON = config.NAMESPACE + "::"
    if args.objects:
        config.PARSE_ACTORS = True
        config.PARSE_BOUNDARIES = True
    if args.objects:
        config.PARSE_ACTORS = True
    if args.objects:
        config.PARSE_BOUNDARIES = True
    if args.globals:
        config.CREATE_GLOBALS_FILE = True
    if args.author_name:
        config.AUTHOR_NAME = args.author_name
    if args.author_mail:
        config.AUTHOR_MAIL = args.author_mail
    if args.header_line:
        config.FILE_HEADER = args.header_line

    with open("graphics/ressources/foton.json", encoding="utf-8") as foton_json:
        if config.TMX_OVERRIDE and config.MAP_NAME:
            foton = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            foton = json.load(foton_json)

        map_data = tm.get_map_data(foton['maps'])
        if not config.PREVENT_MAP_CONSOLIDATION:
            for map_name in map_data["combined_maps"]:
                cmap_data = map_data["combined_maps"][map_name]
                bitmap,tilemap_width,success = tc.create_tilemap(cmap_data,True)
                if success:
                    for combined_map in cmap_data["maps"]:
                        map_data["maps"][combined_map]["combined_tilemap"] = {
                            "mapdict":cmap_data,
                            "bitmap":bitmap,
                            "tilemap_width":tilemap_width
                        }

        for map_name in map_data["maps"]:
            Map = MapObject()
            Map.init(map_data["maps"][map_name])
            Map.gather_map_data()
            Map.calculate_tilemap_data()
            print("Generating map "+Map.name+" with dimensions: "+\
              str(Map.width)+"x"+str(Map.height)
            )

            if not config.FORCE_MAP_DATA_GENERATION and \
               os.path.exists("include/" + Map.name + ".hpp") and \
               os.path.getctime("include/" + Map.name + ".hpp") >= \
                   os.path.getctime(Map.tmx_filepath) and \
               os.path.exists("src/" + Map.name + ".cpp") and \
               os.path.getctime("src/" + Map.name + ".cpp") >= \
                   os.path.getctime(Map.tmx_filepath):
                print("Source tiled map not modified, skipping generation of new data files")
            else:
                write_tilemap_header_file(Map)
                write_tilemap_cpp_file(Map)

    if config.CREATE_GLOBALS_FILE:
        write_tilemap_globals_file()

    print("Finished")
