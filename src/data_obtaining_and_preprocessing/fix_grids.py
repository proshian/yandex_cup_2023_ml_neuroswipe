"""
This script fixed the issue where nearly all keys in each 
grid (keyboard layout) have a width that is 1 unit larger than should be.

## Problem Description:
Each row of keys is arranged in a grid such that keys 
are closely packed without gaps.
Ideally, for keys ordered by increasing `x` position:
`key[i].x + key[i].w == key[i+1].x`.

However, in the dataset, for all keys (except the last key in each row):
`key[i].x + key[i].w = key[i+1].x + 1`.

This discrepancy suggests an error in the dataset 
where `key[i].w` should be `key[i].w - 1`. 

## Proposed Solution:
To fix this issue, the following steps are taken:
1. Split the keys into rows based on their `y` position.
2. Sort the keys in each row by their `x` position.
3. For all keys except the last in a row, 
   if `(key[i].x + key[i].w) - key[i+1].x == 1`, 
   adjust the width as: `key[i].w -= 1`.
4. For the last key in each row, calculate the right padding:
   - `right_padding = grid['width'] - key[-1].x - key[-1].w`
   - `left_padding = key[0].x`
   - If `right_padding - left_padding == 1`, adjust the width as: `key[-1].w -= 1`.
5. Combine all rows back into a single list of keys.


We could fix any overlapping that way, but in general case a bigger overlap 
might need a more thorough investigation, so I fix widths that are only 
larger by 1 for now.
"""

from typing import List, Dict
from copy import deepcopy
import argparse
import json


def group_keys_by_y(keys: List[dict], 
                    perform_deepcopy: bool = True
                    ) -> Dict[int, List[dict]]:
    y_to_keys: Dict[int, List[dict]] = {}
    for key in keys:
        y = key['hitbox']['y']
        if perform_deepcopy:
            key = deepcopy(key)
        y_to_keys.setdefault(y, []).append(key)
    return y_to_keys


def fix_key_widths_by_1__row(keys_row: List[dict], kb_width) -> List[dict]:
    for i in range(len(keys_row) - 1):
        x1 = keys_row[i]['hitbox']['x']
        w1 = keys_row[i]['hitbox']['w']
        x2 = keys_row[i+1]['hitbox']['x']
        diff = (x1 + w1) - x2
        if diff == 1:
            keys_row[i]['hitbox']['w'] -= 1

    padding_left = keys_row[0]['hitbox']['x']
    last_key_x = keys_row[-1]['hitbox']['x']
    last_key_w = keys_row[-1]['hitbox']['w']
    padding_right = kb_width - (last_key_x + last_key_w)
    diff = padding_right - padding_left
    if diff == 1:
        keys_row[-1]['hitbox']['w'] -= 1

    return keys_row


def fix_key_widths_by_1__grid(grid: dict) -> dict:
    y_to_keys = group_keys_by_y(grid['keys'])
    y_sorted = sorted(y_to_keys.keys())
    key_rows = [y_to_keys[y] for y in y_sorted]
    for keys in key_rows:
        keys.sort(key=lambda key: key['hitbox']['x'])

    fixed_key_rows = []
    for keys in key_rows:
        fixed_key_rows.append(fix_key_widths_by_1__row(keys, grid['width']))

    fixed_keys = [key for keys in fixed_key_rows for key in keys]

    fixed_grid = {k: v for k, v in grid.items() if k != 'keys'}
    fixed_grid['keys'] = fixed_keys

    return fixed_grid


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True)
    parser.add_argument('-o', '--output', type=str, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.input, 'r', encoding='utf-8') as f:
        grid_name_to_grid = json.load(f)
    fixed_grid_name_to_grid = {
        name: fix_key_widths_by_1__grid(grid)
        for name, grid in grid_name_to_grid.items()}
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(fixed_grid_name_to_grid, f, ensure_ascii=False, separators=(',', ':'), indent=2)


if __name__ == '__main__':
    main()
