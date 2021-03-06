import os
from datetime import datetime

from source import datamodule
from source.util import *

from pytorch_lightning import Trainer
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.callbacks import ModelCheckpoint


def Model_Info(model):
    
    if model == 'Toppop': info = {'type' : 'rb', 'datamodule' : 'Loader'}
    elif model == 'Random': info = {'type' : 'rb', 'datamodule' : 'Loader'}
    elif model == 'SVM' : info = {'type' : 'nn', 'datamodule' : 'PairLoader'}
    elif model == 'CML' : info = {'type' : 'nn', 'datamodule' : 'TripletLoader'}
    elif model == 'SymML' : info = {'type' : 'nn', 'datamodule' : 'TripletLoader'}
    else :
        raise NameError
        
    return info
    
    
def fit_model(model, args):
    from scipy.sparse import load_npz
    model_info = Model_Info(model.__name__)
    
    # Train dataset
    DATASET_PATH = get_current_path(args.path, args.nsml)
    
    train_adj = load_npz(os.path.join(DATASET_PATH,
                                      args.ADJ,
                                      'train_adj.npz'))
    
    n_usr, n_msg = train_adj.shape
    
    # Define datamodule
    _datamodule = getattr(datamodule, model_info['datamodule'])

    train_module = _datamodule(train_adj, args)
    
    # Define model
    _model = model(n_usr, n_msg, **vars(args))
    
    
    if model_info['type'] is 'nn':
        
        current_time = datetime.now().strftime("%y%m%d_%H%M%S")
    
        # Define Callback
        checkpoint_callback = ModelCheckpoint(save_top_k = -1)

        logger = TensorBoardLogger(
            save_dir = DATASET_PATH,
            version = f'{model.__name__}_{current_time}_usr_dim_{args.usr_dim}_msg_dim_{args.msg_dim}',
            name='lightning_logs'
        )

        trainer = Trainer.from_argparse_args(args,
                                             callbacks=[checkpoint_callback],
                                             logger = logger)

        trainer.fit(_model, train_module)
        
    else :
        _model.fit(train_module)
    
    return _model