import pickle
from typing import Dict, Tuple, Iterable, List

from grid_processing_utils import get_kb_label


def _group_keys_by_y(keys: List[dict]) -> Dict[int, List[dict]]:
    y_to_keys = {}
    for key in keys:
        y = key['hitbox']['y']
        y_to_keys.setdefault(y, []).append(key)
    return y_to_keys


def clip(x, a_min, a_max):
    return min(max(x, a_min), a_max)


def get_rows(keys: List[dict], allowed_width_deviation: float
             ) -> Tuple[List[List[str]], List[int], List[float], int, int]:
    """
    Creates innerstate for NearestKeyLookup.

    Creates a `rows` list of key rows where each row is 
    an ordered lsit of unique charrecters representing a sequence labels
    of keys in a corresponding row. Also creates metadata that can be
    used together with `rows` to determine the nearest key label 
    for a given (x, y) coordinate.

    Ensures it can be represented as a grid.
    A valid grid satisfies:
    - All keys within a row have approximately the same width.
    - All keys have the same height.
    - All keys within a row touch horizontally.
    - All rows touch vertically.

    Arguments:
    ----------
    keys: List[dict]
        List of keyboard keys represented as a dict with a label and a hitbox.
    allowed_width_difference: float 
        Maximum allowed difference in width relative to mean per row.

    Returns:
    --------
    Optional[Tuple]: 
        - rows (List[List[str]]): Key labels organized into rows.
        - x_offsets (List[int]): X-coordinates of the leftmost keys in each row.
        - mean_widths (List[float]): Mean widths of keys in each row.
        - key_height (int): Height of the keys.
        - keyboard_y_offset (int): Y-offset of the topmost row.
        Returns `None` if the grid constraints are not satisfied.
    """    
    y_to_keys = _group_keys_by_y(keys)
    ys = sorted(y_to_keys.keys())
    keyboard_y_offset = ys[0]
    key_rows = [y_to_keys[y] for y in ys]
    
    mean_widths = [sum([key['hitbox']['w'] for key in row]) / len(row) 
                   for row in key_rows]

    for i, (row, mean_width) in enumerate(zip(key_rows, mean_widths)):
        for key in row:
            width = key['hitbox']['w']
            if abs(width - mean_width) > allowed_width_deviation:
                raise ValueError(
                    f"Key width deviation too high in row {i}. \n" \
                    f"Key width: {width}, mean width: {mean_width}")

    for row in key_rows:
        row.sort(key=lambda key: key['hitbox']['x'])

    x_offsets = [row[0]['hitbox']['x'] for row in key_rows]

    # Ensure keys within each row are touching
    for row in key_rows:
        for i in range(len(row) - 1):
            if row[i]['hitbox']['x'] + row[i]['hitbox']['w'] < row[i + 1]['hitbox']['x']:
                raise ValueError("Keys are not touching in a row")

    key_heights = set(key['hitbox']['h'] for row in key_rows for key in row)
    if len(key_heights) != 1:
        raise ValueError("Keys have different heights")
    key_height = key_heights.pop()

    # Ensure all rows are touching
    for i in range(len(key_rows) - 1):
        cur_y = key_rows[i][0]['hitbox']['y']
        next_y = key_rows[i + 1][0]['hitbox']['y']
        if cur_y + key_height != next_y:
            raise ValueError(f"Rows are not touching: {cur_y + key_height} != {next_y}")
            
    rows = [[get_kb_label(key) for key in row] for row in key_rows]

    return rows, x_offsets, mean_widths, key_height, keyboard_y_offset
    
    
    
class NearestKeyLookup:
    """
    Given a keyboard grid and a list of nearest_key_candidates
    returns the nearest key label for a given (x, y) coordinate.

    Stores a keyboard as a list of rows. Each row is a list of key labels (string).
    To find the nearest key label for a given (x, y) coordinate,
    we determine the row and column of the coordinate in the described structure.
    """

    def __init__(self, 
                 grid: dict, 
                 allowed_keys: Iterable[str],
                 allowed_width_difference: float = 1.1) -> None:
        filtered_keys = [key for key in grid['keys'] if get_kb_label(key) in allowed_keys]
        (self.rows, 
         self.x_offsets, 
         self.mean_widths, 
         self.key_height,
         self.keyboard_y_offset) = get_rows(filtered_keys, allowed_width_difference)
        self.kb_width = grid['width']
        self.kb_height = grid['height']
        self.nearest_key_labels_dict = {}
        self._populate_nearest_key_labels_dict()

    def _populate_nearest_key_labels_dict(self):
        """
        Populates the `nearest_key_labels_dict` for all positions within the keyboard.
        """
        for x in range(self.kb_width):
            for y in range(self.kb_height):
                analytical_key_label, is_correctness_guaranteed = (
                    self._get_nearest_kb_key_label_analytically(x, y))
                if is_correctness_guaranteed:
                    continue
                key_label = self._get_nearest_kb_key_label_via_distance(x, y)
                if analytical_key_label != key_label:
                    self.nearest_key_labels_dict[(x, y)] = key_label

    def _get_nearest_kb_key_label_via_distance(self, x: int, y: int) -> str:
        """
        Finds the nearest key label by calculating distances to key centers.
        """
        min_distance = float('inf')
        nearest_key_label = None

        for row_idx, row in enumerate(self.rows):
            for col_idx, key_label in enumerate(row):
                key_center_x = self.x_offsets[row_idx] + col_idx * self.mean_widths[row_idx] + self.mean_widths[row_idx] / 2
                key_center_y = self.keyboard_y_offset + row_idx * self.key_height + self.key_height / 2
                distance = ((x - key_center_x) ** 2 + (y - key_center_y) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    nearest_key_label = key_label

        return nearest_key_label


    def __call__(self, x, y):
        return self.get_nearest_kb_key_label(x, y)
        
    def get_nearest_kb_key_label(self, x: int, y: int):
        """
        Returns the nearest key label for a given (x, y) coordinate.
        """
        key_label, is_correctness_guaranteed = (
            self._get_nearest_kb_key_label_analytically(x, y))
        if is_correctness_guaranteed:
            return key_label
        
        is_inside_keyboard = x < self.kb_width and y < self.kb_height
        if is_inside_keyboard:
            return self.nearest_key_labels_dict.get((x, y), key_label)

        return self._get_nearest_kb_key_label_via_distance(x, y)

        
    def _get_right_offset(self, row_idx: int) -> int:
        """
        Returns the right offset of the row.
        """
        row = self.rows[row_idx]
        left_offset = self.x_offsets[row_idx]
        total_row_width = self.mean_widths[row_idx] * len(row)
        return self.kb_width - left_offset - total_row_width
        
    
    def _get_nearest_kb_key_label_analytically(self, x: int, y: int) -> Tuple[str, bool]:
        """
        Uses the `rows` list to determine the nearest key 
        label for a given (x, y) coordinate.

        If the coordinate is outside the keyboard grid,
        the col_idx and row_idx are clipped to the valid range.
        This may lead to incorrect results. The `is_correctness_guaranteed`
        flag is set to False in such cases. 
        Note that `is_correctness_guaranteed` may be True even if the
        coordinate is outside the grid if some euristic allows us to
        determine the nearest key label correctly.

        Returns
        -------
        Tuple[key_label, is_correctness_guaranteed]:
        key_label: str
            The label of the nearest key.
        is_correctness_guaranteed: bool
            Whether the returned key label is guaranteed to be correct.
        """
        is_correctness_guaranteed = True

        row_idx = int((y - self.keyboard_y_offset) // self.key_height)

        # If there is no LEFT or RIGHT offset in the first row and we are above all keys,
        # the resulting nearest key would be the same as if we were in the first row. 
        above_all_keys = y < self.keyboard_y_offset
        first_row_left_offset = self.x_offsets[0]
        first_row_right_offset = self._get_right_offset(0)
        if (
            above_all_keys
            and first_row_left_offset == 0
            and first_row_right_offset <= 0
        ):
            row_idx = 0

        if row_idx < 0 or row_idx >= len(self.rows):
            is_correctness_guaranteed = False

        row_idx_clipped = clip(row_idx, a_min = 0, a_max = len(self.rows)-1)
        row = self.rows[row_idx_clipped]

        left_offset = self.x_offsets[row_idx_clipped]
        key_width = self.mean_widths[row_idx_clipped]
        col_idx = int((x - left_offset) // key_width)


        if col_idx < 0 or col_idx >= len(row):
            is_correctness_guaranteed = False
        
        col_idx_clipped = clip(col_idx, a_min = 0, a_max = len(row)-1)

        return row[col_idx_clipped], is_correctness_guaranteed
    
        
    def _get_state_dict(self) -> dict:
        return {
            'rows': self.rows,
            'x_offsets': self.x_offsets,
            'mean_widths': self.mean_widths,
            'keyboard_y_offset': self.keyboard_y_offset,
            'key_height': self.key_height,
            'nearest_key_labels_dict': self.nearest_key_labels_dict,
        }

    def save_state(self, path: str) -> None:
        """
        Saves the current state of the object to a file.
        """
        state = self._get_state_dict()
        with open(path, 'wb') as f:
            pickle.dump(state, f)

    @classmethod
    def from_state_dict(cls, path: str):
        """
        Loads the object state from a file.
        """
        with open(path, 'rb') as f:
            state = pickle.load(f)
        obj = cls.__new__(cls)
        obj.rows = state['rows']
        obj.x_offsets = state['x_offsets']
        obj.mean_widths = state['mean_widths']
        obj.keyboard_y_offset = state['keyboard_y_offset']
        obj.key_height = state['key_height']
        obj.nearest_key_labels_dict = state['nearest_key_labels_dict']
        return obj
