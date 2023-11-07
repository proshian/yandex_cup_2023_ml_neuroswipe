import torch

from utils import prepare_batch, turncate_traj_batch


class GreedyGenerator:
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = torch.device(device)
        self.model.to(self.device)
        self.eos_token_id = tokenizer.char_to_idx['<eos>'] 

    def __call__(self, xyt, kb_tokens, traj_pad_mask, max_steps_n=35):
        with torch.no_grad():

            tokens = [self.tokenizer.char_to_idx['<sos>']]

            
            xyt, kb_tokens, traj_pad_mask = (el.unsqueeze(0) for el in (xyt, kb_tokens, traj_pad_mask))
            # xyt, kb_tokens, traj_pad_mask = turncate_traj_batch(xyt, kb_tokens, traj_pad_mask)
            xyt, kb_tokens, traj_pad_mask = (el.to(self.device) for el in (xyt, kb_tokens, traj_pad_mask))
            xyt, kb_tokens = (el.transpose(0, 1) for el in (xyt, kb_tokens))


            encoded = self.model.encode(xyt, kb_tokens, traj_pad_mask)

        
            for _ in range(max_steps_n):
                
                dec_in_char_seq = torch.tensor(tokens).unsqueeze(0).to(self.device)
                word_pad_mask = torch.zeros_like(dec_in_char_seq, dtype=torch.bool, device=self.device)
                dec_in_char_seq.transpose_(0,1)


                x = [xyt, kb_tokens, dec_in_char_seq, traj_pad_mask, word_pad_mask]
                x = [el.unsqueeze(0) for el in x]
                next_tokens_logits = self.model.decode(encoded, dec_in_char_seq, traj_pad_mask, word_pad_mask).transpose_(0, 1)[0, -1]
                best_next_token = next_tokens_logits.argmax()  # batch_i = 0, decoder_out_onehot_vector_seq_i = -1 
                if best_next_token == self.eos_token_id:
                    break

                tokens.append(int(best_next_token))
        
            return self.tokenizer.decode(tokens[1:])
    



# The class below is not finished. It's suposed that we process
# multiple curves simpultaniously. At each step we check 
# if all batch out sequences have <eos> token. If true,
# generation is finished 


class GreedyGeneratorBatched:
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = torch.device(device)
        self.model.to(self.device)
        self.eos_token_id = tokenizer.char_to_idx['<eos>'] 

    def __call__(self,
                 xyt,  # (batch_size, curves_seq_len, n_coord_feats)
                 kb_tokens,  # (batch_size, curves_seq_len)
                 traj_pad_mask,  # (batch_size, curves_seq_len)
                 max_steps_n=35):
        batch_size, curves_seq_len, n_coord_feats = xyt.shape

        # (batch_size, chars_seq_len)
        dec_in_char_seq = torch.full((batch_size, 1), self.tokenizer.char_to_idx['<sos>'], dtype=torch.int, device=self.device)

        # We don't have to put everything to device because it's done in prepare_batch.

        with torch.no_grad():
            for _ in range(max_steps_n):
                word_pad_mask = None
                # dummy_y is any tensor with n_dims = 2 (chars_seq_len - 1, batch_size).
                dummy_y = torch.tensor([[1]])
                x = (xyt, kb_tokens, dec_in_char_seq, traj_pad_mask, word_pad_mask)
                model_input, dummy_y = prepare_batch(x, dummy_y, self.device)
                one_hot_token_logits = self.model.apply(*model_input).transpose_(0, 1)  # (batch_size, chars_seq_len, vocab_size)
                best_next_tokens = one_hot_token_logits[:, -1].argmax(dim=1)  # (batch_size)

                print(best_next_tokens.shape, dec_in_char_seq.shape)

                dec_in_char_seq = torch.cat((dec_in_char_seq, best_next_tokens.unsqueeze(0)), dim=0)
                kb_tokens.transpose_(0, 1)
                xyt.transpose_(0,1)

        predictions = [self.tokenizer.decode(dec_in_char_seq[i].tolist()) for i in range(batch_size)]
        
        return predictions