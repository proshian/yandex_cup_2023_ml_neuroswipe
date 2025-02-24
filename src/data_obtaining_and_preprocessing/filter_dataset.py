from typing import Dict, List, Optional
import json
import os
import argparse

from data_obtaining_and_preprocessing.swipe_validity import (
    monotoniacally_increases, 
    points_not_too_far, 
    over_two_points_in_each_segment
)
from grid_processing_utils import (
    get_label_to_key_map,
    get_kb_key_center,
    distance
)

from tqdm import tqdm


def create_dataset_without_errors(dataset_path: str,
                                  out_path: str,
                                  max_dist: int,
                                  grids: Dict[str, dict] = None,
                                  total: Optional[int] = None) -> Dict[str, List[int]]:
    """
    Creates a version of a given dataset with invalid data filtered out.

    Arguments:
    ----------
    grids: str
        Dict with `grid names` as keys and `grids` as values.
        If grids is None
            it's supposed that the dataset is in original
            format (curves in the dataset don't have
            grid_name attribute, but have grid attribute with
            full grid information).
        Else
            Curves have grid_name attribute and don't have 
            grid attribute

    Returns:
    --------
    Dict with keys as error types and values as lists of indexes
    of lines in the dataset that have this error.
    """
    is_inplace = (os.path.abspath(dataset_path) == os.path.abspath(out_path))
    temp_out_path = out_path + '.tmp' if is_inplace else out_path
    
    error_logs = {
        'non_monotonic_timestamps': [],
        'points_too_far': [],
        'insufficient_points_in_segment': []
    }
    
    with open(dataset_path, encoding="utf-8") as f:
        for i, line in tqdm(enumerate(f), total=total):
            line_data = json.loads(line)

            c = line_data['curve']
            x, y, t = c['x'], c['y'], c['t']
            if grids is not None:
                kb_keys = grids[c['grid_name']]['keys']
            else:
                kb_keys = c['grid']['keys']

            # Check each condition separately
            monotonic_ok = monotoniacally_increases(t)
            points_ok = points_not_too_far(x, y, kb_keys, max_dist)
            segments_ok = over_two_points_in_each_segment(
                line_data['word'], 
                x, y,
                get_label_to_key_map(kb_keys),
                absent_chars_on_keyboard=('-',))
            
            # Log errors
            if not monotonic_ok:
                error_logs['non_monotonic_timestamps'].append(i)
            if not points_ok:
                error_logs['points_too_far'].append(i)
            if not segments_ok:
                error_logs['insufficient_points_in_segment'].append(i)

            has_error = not (monotonic_ok and points_ok and segments_ok)
            
            if has_error:
                continue

            with open(temp_out_path, 'a', encoding="utf-8") as out_f:
                out_f.write(line)
    
    if is_inplace:
        os.replace(temp_out_path, out_path)
    
    return error_logs

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_path', type=str, required=True)
    parser.add_argument('--grids_path', type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    parser.add_argument('--log_dir', type=str, required=True)
    return parser.parse_args()

def main():
    args = parse_args()

    with open(args.grids_path, "r", encoding="utf-8") as f:
        grids = json.load(f)
    
    # Calculate max_dist for `default` grid 
    grid_name = 'default'
    label2key = get_label_to_key_map(grids[grid_name]['keys'])
    max_dist = distance(
        *get_kb_key_center(label2key['ф']['hitbox']),
        *get_kb_key_center(label2key['ц']['hitbox'])
    )

    FULL_TRAIN_DATASET_LENGTH = 6_000_000

    error_logs = create_dataset_without_errors(
        dataset_path=args.dataset_path,
        out_path=args.output_path,
        max_dist=max_dist,
        grids=grids,
        total=FULL_TRAIN_DATASET_LENGTH  
    )


    os.makedirs(args.log_dir, exist_ok=True)
    for error_type, indexes in error_logs.items():
        log_file = os.path.join(args.log_dir, f"{error_type}.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            for idx in indexes:
                f.write(f"{idx}\n")

if __name__ == "__main__":
    main()
