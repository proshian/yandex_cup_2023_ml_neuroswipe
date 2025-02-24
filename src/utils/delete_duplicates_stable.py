from typing import Iterable

def delete_duplicates_stable(lst: Iterable) -> list:
    """
    Deletes duplicates from an iterable. Maintains the order of elements.
    """
    new_lst = []
    new_lst_set = set()
    for el in lst:
        if el not in new_lst_set:
            new_lst.append(el)
            new_lst_set.add(el)
    return new_lst
