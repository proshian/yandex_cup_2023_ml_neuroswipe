from typing import List, Tuple

from data_analysis.get_segments import get_segments
from grid_processing_utils import get_kb_key_center, distance, get_key_centers


def monotoniacally_increases(time: List[int]) -> bool:
    for i, t in enumerate(time[1:], 1):
        if t <= time[i-1]:
            return False
    return True


def points_not_too_far(x_list: List[int],
                       y_list: List[int],
                       kb_keys: dict,
                       max_dist: int) -> bool:
    for x, y in zip(x_list, y_list):
        not_too_far = False
        for key in kb_keys:
            key_x, key_y = get_kb_key_center(key['hitbox'])
            dist = distance(x, y, key_x, key_y)
            if dist < max_dist:
                not_too_far = True
                break
        if not not_too_far:
            return False
    return True  


def n_segments_is_correct(tgt_word, segments):
    # тут не учтено, что в слове нужно произвести замены (например, 'ъ' на 'ь', 'ё' на 'е')
    # а также удалить пунктуацию (вроде бы только дефис)
    # причем удаление и замены нужно делать до того, как делать colapsed word,
    # иначе примеры вроде из-за будут ломать проверку
    word_without_hyphen = ""
    for c in tgt_word:
        if c != '-':
            word_without_hyphen += c
    
    collapsed_word = ""
    for i, c in enumerate(word_without_hyphen):
        if (i < (len(word_without_hyphen) - 1) and c == word_without_hyphen[i+1]):
            continue
        collapsed_word += c

    if len(segments) != len(collapsed_word):
        print(collapsed_word)

    return len(segments) == len(collapsed_word)



def over_two_points_in_each_segment(tgt_word: str,
                                    x: List[int],
                                    y: List[int],
                                    label2key: dict,
                                    absent_chars_on_keyboard: Tuple = ()) -> bool:
    threshold_len = 2

    key_centers = get_key_centers(tgt_word, label2key, absent_chars_on_keyboard)
    segments = get_segments(key_centers, x, y)

    if not n_segments_is_correct(tgt_word, segments):
        print(f"Warning: n_segments = {len(segments)} for {tgt_word} and {segments}")
    
    for segment in segments:
        if len(segment) < threshold_len:
            return False
    return True
