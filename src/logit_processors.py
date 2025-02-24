from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Set
from collections import defaultdict

import torch
from torch import Tensor

from ns_tokenizers import CharLevelTokenizerv2


class LogitProcessor(ABC):
    @abstractmethod
    def process(self, logits: Tensor, input_ids: List[int]) -> Tensor:
        pass


class VocabularyLogitProcessor(LogitProcessor):
    """
    Mask out the tokens that can't follow the generated prefix.
    """
    def __init__(self, tokenizer: CharLevelTokenizerv2, 
                 vocab: List[str], max_token_id: int) -> None:
        """
        Arguments:
        ----------
        vocab: Optional[List[str]]
            List of all possible words.
            It's used to mask out the tokens that can't follow
            generated prefix.
            If vocab is provided, max_token_id must be provided too.
        max_token_id: Optional[int]
            The maximum token id that can be generated.
            A model might never generate some tokens. For example,
            we never need to generate <pad> or <sos> tokens.
            max_token_id == n_out_neurons - 1 == n_classes - 1.
            It's supposed that if model doesn't generate some tokens,
            the unallowed tokens correspond to the last n_tokens - n_out_neurons
            tokens in the tokenizer.
        """
        self.tokenizer = tokenizer
        self.vocab = vocab
        self.max_token_id = max_token_id
        self.prefix_to_allowed_ids = self._create_prefix_to_allowed_ids(vocab)

    def _create_prefix_to_allowed_ids(self, vocab: List[str]) -> Dict[Tuple[int, ...], Set[int]]:
        # ! When switching to another type of tokenizer where tokens are not just characters
        # but can be a sequence of characters, we need to change the implementation of this method. 
        prefix_to_allowed_ids = defaultdict(set)
        for word in vocab:
            tokenized_word = self.tokenizer.encode(word)
            for i in range(1, len(tokenized_word)):
                prefix = tuple(tokenized_word[:i])
                prefix_to_allowed_ids[prefix].add(tokenized_word[i])
        return prefix_to_allowed_ids

    def _get_unallowed_token_ids(self, prefix_ids: List[int]) -> Set[int]:
        allowed_ids = self.prefix_to_allowed_ids[tuple(prefix_ids)]
        all_ids = set(self.tokenizer.idx_to_char.keys())
        impossible_ids = set(range(self.max_token_id + 1, len(self.tokenizer.char_to_idx)))
        unallowed_ids = all_ids - allowed_ids - impossible_ids
        return unallowed_ids

    def process(self, logits: Tensor, prefix_ids: List[int]) -> Tensor:
        unallowed_ids = self._get_unallowed_token_ids(prefix_ids)
        logits[torch.tensor(list(unallowed_ids), dtype = torch.int)] = float('-inf')
        return logits
