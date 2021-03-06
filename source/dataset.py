import os
import queue
import threading

import torch
import numpy as np

from .util import get_current_path

class tch_Dataset(torch.utils.data.Dataset):
    def __init__(self, pos_pairs, neg_pairs, idx2usr_id, idx2msg_id, 
                 DATASET_PATH, **kwargs):
        
        super().__init__()
        
        self.pos_usr_msg_pair = pos_pairs
        self.neg_usr_msg_pair = neg_pairs
        
        self.idx2usr_id = idx2usr_id
        self.idx2msg_id = idx2msg_id
        
        self.DATASET_PATH = DATASET_PATH
        
    def usr_idx2feat(self, usr_idx):
        
        nv_id = self.idx2usr_id[usr_idx]
        
        DATAPATH = os.path.join(self.DATASET_PATH,
                                f"data/users/starts_with_{nv_id[:2]}/{nv_id}.npy")
            
        return torch.from_numpy(np.load(DATAPATH)).float()
    
    def msg_idx2feat(self, msg_idx):
        
        seq = self.idx2msg_id[msg_idx]
        
        DATAPATH = os.path.join(self.DATASET_PATH, f"data/items/{seq}.npy")
            
        return torch.from_numpy(np.load(DATAPATH)).float()


    
class PairDataset(tch_Dataset):
    
    def __init__(self, pos_pairs, neg_pairs, idx2usr_id, idx2msg_id,
                 DATASET_PATH, **kwargs):
        
        super().__init__(pos_pairs, neg_pairs, idx2usr_id, idx2msg_id,
                         DATASET_PATH, **kwargs) 
        
        pos_usr_msg_pair = np.concatenate([self.pos_usr_msg_pair, np.ones((self.pos_usr_msg_pair.shape[0], 1))], 
                                           axis = 1)
        
        neg_usr_msg_pair = np.concatenate([self.neg_usr_msg_pair, np.zeros((self.neg_usr_msg_pair.shape[0], 1))], 
                                           axis = 1)
        
        del self.pos_usr_msg_pair
        del self.neg_usr_msg_pair
        
        self.usr_msg_pair = np.concatenate([pos_usr_msg_pair, neg_usr_msg_pair], 
                                           axis = 0).astype(np.int)
    
    def __len__(self):
        return self.usr_msg_pair.shape[0]
    
    def __getitem__(self, idx):
        usr, msg, y = self.usr_msg_pair[idx]
        
        usr_feat = self.usr_idx2feat(usr)
        msg_feat = self.msg_idx2feat(msg)
        
        return usr_feat, msg_feat, y
    
    
    
    
    
class TripletDataset(tch_Dataset): 
    def __init__(self, pos_pairs, neg_pairs, idx2usr_id, idx2msg_id,
                 DATASET_PATH, **kwargs):
        
        super().__init__(pos_pairs, neg_pairs, idx2usr_id, idx2msg_id,
                         DATASET_PATH, **kwargs)
        
        self.n_negative = kwargs.get('n_negative')
        
        
    def __len__(self):
        return self.pos_usr_msg_pair.shape[0]
    
    def __getitem__(self, idx):
        
        usr, msg = self.pos_usr_msg_pair[idx]
        
        users_neg = self.neg_usr_msg_pair[msg]

        # sample negative samples(users)
        
        neg_sample = np.random.choice(users_neg, size=self.n_negative)

        pos_usr_feat = self.usr_idx2feat(usr)
        pos_msg_feat = self.msg_idx2feat(msg)
        
        q = queue.Queue()
        neg_usr_feat = [None] * self.n_negative

        for i, neg_usr in enumerate(neg_sample):
            thread = threading.Thread(target = self.usr_idx2featQ, args = (neg_usr, q, i))
            thread.start()

        for _ in range(len(neg_sample)):
            usr_feat, idx = q.get()
            neg_usr_feat[idx] = usr_feat
            
        thread.join()
        
        neg_usr_feat = torch.stack(neg_usr_feat).float()
        
        pos_pairs = (usr.astype('long'), pos_usr_feat), (msg.astype('long'), pos_msg_feat)

        return pos_pairs, (neg_sample.astype('long'), neg_usr_feat)


    def usr_idx2featQ(self, usr_idx, q, idx):
        
        nv_id = self.idx2usr_id[usr_idx]
        
        DATAPATH = os.path.join(self.DATASET_PATH, 
                                f"data/users/starts_with_{nv_id[:2]}/{nv_id}.npy")
            
        return q.put((torch.from_numpy(np.load(DATAPATH)).float(), idx))


    