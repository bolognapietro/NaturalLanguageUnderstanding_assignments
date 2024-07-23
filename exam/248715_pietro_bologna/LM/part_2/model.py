import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import math
import numpy as np
import torch.distributions.bernoulli as brn
from utils import VariationalDropout

class RNN_cell(nn.Module):
    def __init__(self,  hidden_size, input_size, output_size, vocab_size, dropout=0.1):
        super(RNN_cell, self).__init__()
        
        self.W = nn.Linear(input_size, hidden_size, bias=False)
        self.U = nn.Linear(hidden_size, hidden_size)
        self.V = nn.Linear(hidden_size, vocab_size)
        self.vocab_size = vocab_size
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, prev_hidden, word):
        input_emb = self.W(word)
        prev_hidden_rep = self.U(prev_hidden)
        # ht = σ(Wx + Uht-1 + b)
        hidden_state = self.sigmoid(input_emb + prev_hidden_rep)
        # yt = σ(Vht + b)
        output = self.output(hidden_state)
        return hidden_state, output
    
class LM_RNN(nn.Module):
    def __init__(self, emb_size, hidden_size, output_size, pad_index=0, out_dropout=0.1,
                 emb_dropout=0.1, n_layers=1):
        super(LM_RNN, self).__init__()
        # Token ids to vectors, we will better see this in the next lab 
        self.embedding = nn.Embedding(output_size, emb_size, padding_idx=pad_index)
        # Pytorch's RNN layer: https://pytorch.org/docs/stable/generated/torch.nn.RNN.html
        self.rnn = nn.RNN(emb_size, hidden_size, n_layers, bidirectional=False, batch_first=True)    
        self.pad_token = pad_index
        # Linear layer to project the hidden layer to our output space 
        self.output = nn.Linear(hidden_size, output_size)
        
    def forward(self, input_sequence):
        emb = self.embedding(input_sequence)
        rnn_out, _  = self.rnn(emb)
        output = self.output(rnn_out).permute(0,2,1)
        return output 

class LSTM_RNN(nn.Module):
    def __init__(self, emb_size, hidden_size, output_size, pad_index=0, out_dropout=0.1, emb_dropout=0.1, n_layers=1):
        super(LSTM_RNN, self).__init__()
        # Token ids to vectors, we will better see this in the next lab
        self.embedding = nn.Embedding(output_size, emb_size, padding_idx=pad_index)
        
        self.lstm = nn.LSTM(emb_size, hidden_size, n_layers, bidirectional=False, batch_first=True)
        self.output = nn.Linear(hidden_size, output_size)
        self.pad_token = pad_index

    def forward(self, input_sequence):
        emb = self.embedding(input_sequence)

        lstm_out, _  = self.lstm(emb)
        
        output = self.output(lstm_out).permute(0,2,1)
        return output
    
class VariationalDropout(nn.Module):
    def __init__(self):
        super().__init__()
        self.mask = None

    def forward(self, input, dropout=0.5):
        if not self.training or not dropout:
            return input
        if self.mask is None:
            mask = torch.empty(input.size(), device=input.device).bernoulli_(1 - dropout)
            mask = mask / (1 - dropout)
            self.mask = mask * input

        return self.mask

class LSTM_RNN_DROP(nn.Module):
    def __init__(self, emb_size, hidden_size, output_size, pad_index=0, out_dropout=0.1, emb_dropout=0.1, n_layers=1, weight_tying=False, variational_drop=False):
        super(LSTM_RNN_DROP, self).__init__()
        
        self.weight_tying = weight_tying
        self.variational_drop = variational_drop

        # Token ids to vectors, we will better see this in the next lab
        self.embedding = nn.Embedding(output_size, emb_size, padding_idx=pad_index)
        
        # Add one dropout layer after the embedding layer
        if self.variational_drop:
            self.emb_dropout = VariationalDropout()  # Variational dropout
        else:
            self.emb_dropout = nn.Dropout(emb_dropout)  # Normal dropout           

        self.lstm = nn.LSTM(emb_size, hidden_size, n_layers, bidirectional=False, batch_first=True)
        self.output = nn.Linear(hidden_size, output_size)
        self.pad_token = pad_index

        # Add one dropout layer after the LSTM layer
        if self.variational_drop:
            self.out_dropout = VariationalDropout()
        else:
            self.out_dropout = nn.Dropout(out_dropout)
            
        # Weight Tying 
        if self.weight_tying:
            self.output.weight = self.embedding.weight
        
    def forward(self, input_sequence):
        emb = self.embedding(input_sequence)
        if self.variational_drop:
            emb = self.emb_dropout(emb)

        lstm_out, _  = self.lstm(emb)
        if self.variational_drop:
            lstm_out = self.out_dropout(lstm_out)

        output = self.output(lstm_out).permute(0,2,1)
        return output