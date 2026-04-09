#ifndef CONSTANTS_H
#define CONSTANTS_H

#include <vector>
#include <string>

const int SCREEN_WIDTH = 960;
const int SCREEN_HEIGHT = 540;
const float FOV = 66.0f * (3.14159265f / 180.0f);
const float MAX_DIST = 32.0f;
const int RENDER_SCALE = 2;

// Mapa inicial (Cópia do Python)
inline std::vector<std::string> map_0 = {
    "########################",
    "#......#...............#",
    "#..##..#..##...#####...#",
    "#......#.......#.......#",
    "#..#.......#...#..###..#",
    "#..#..###..#...#.......#",
    "#..#.......#...#####...#",
    "#......#...........#...#",
    "########..##########...#",
    "#......................#",
    "#......#.......#.......#",
    "########################"
};

#endif
