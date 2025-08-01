
import torch 
import torch.nn as nn
import math


def scaled_dot_product_attention(q, k, v, mask=None, past_k = None, past_v = None, is_autoregressive= True): #(batch_size, seq_len_k, d_k) or (batch_size,num_heads, seq_len_k, d_k)
    if past_k is not None and past_v is not None:
        assert past_k.shape == past_v.shape
        k = torch.cat([past_k, k], dim = -2) # torch.cat([tensor1, tensor2, ...])
        v = torch.cat([past_v, v], dim = -2)
    scores = torch.matmul(q, k.transpose(-2, -1))
    scaled_scores = scores/math.sqrt(k.size(-1)) 
    if is_autoregressive:
        if mask is None: 
            seq_len_q = scores.size(-2) # negative because num_heads might be or not be there
            seq_len_k = scores.size(-1)
            mask = torch.tril(torch.ones(seq_len_q, seq_len_k, device=q.device)).bool()
            mask = mask.unsqueeze(0).unsqueeze(0)  # shape (1, 1, seq_len_q, seq_len_k) 1 -> all the batches
        scaled_scores = scaled_scores.masked_fill(mask == 0, -float('inf'))
    scaled_scores = scaled_scores - scaled_scores.max(dim=-1, keepdim=True).values #Prevents softmax overflow by centering scores.
    attn_weights = torch.softmax(scaled_scores, dim = -1) 
    return torch.matmul(attn_weights, v)





class MultiHeadSelfAttention(nn.Module):
    def __init__(self, embed_dim, num_heads, is_autoregressive = True):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.q_projection_layer = nn.Linear(embed_dim, embed_dim) 
        self.k_projection_layer = nn.Linear(embed_dim, embed_dim) 
        self.v_projection_layer = nn.Linear(embed_dim, embed_dim) 
        self.final_projection_layer = nn.Linear(embed_dim, embed_dim) 
        self.embed_dim = embed_dim
        self.layer_norm = nn.LayerNorm(self.embed_dim)
        self.is_autoregressive = is_autoregressive
        
    def forward(self, input, past_k=None, past_v=None):
        q = self.q_projection_layer(input)
        k = self.k_projection_layer(input)
        v = self.v_projection_layer(input)
        [batch_size, seq_len, embed_dim] = q.size() # or batch_size, seq_len, embed_dim = q.size() - they both work
        assert embed_dim % self.num_heads == 0
        head_dim = int(embed_dim//self.num_heads)
        q = q.reshape([batch_size, seq_len, self.num_heads, head_dim]).transpose(1, 2)
        k = k.reshape([batch_size, seq_len, self.num_heads, head_dim]).transpose(1, 2)
        v = v.reshape([batch_size, seq_len, self.num_heads, head_dim]).transpose(1, 2)
        
        attn_out = scaled_dot_product_attention(q, k, v, mask = None, past_k = past_k, past_v = past_v, is_autoregressive = self.is_autoregressive)
        # for head in self.num_heads:  prevents GPU from parallelizing operations efficiently and introduces slow Python-level control flow.
        #     attn_out = scaled_dot_product_attention(q[:, :, head, :], k[:, :, head, :], v[:, :, head, :])
        attn_out = attn_out.transpose(1, 2).reshape([batch_size, seq_len, embed_dim])
        assert attn_out.shape == input.shape
        attn_out = self.final_projection_layer(attn_out)
        attn_out_and_input = attn_out + input 
        return self.layer_norm(attn_out_and_input) ,attn_out, k, v #This is post-norm, used in older models. Most modern architectures like GPT-2/3 use pre-norm: x_norm = self.layer_norm(input)
    
    #detatching: not compute gradients - we can do it in inference where we are not training and we want to save memory, or when we dont want the information of the gradient of a specific variable in our trainign because it would be cheating from the labels
    
    
    
    
    
    
    
    
    
