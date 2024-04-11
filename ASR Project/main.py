import torch
import queue
import os
import random
import warnings
import time
import json
import argparse
from glob import glob

from modules.preprocess import preprocessing
from modules.trainer import trainer
from modules.utils import (
    get_optimizer,
    get_criterion,
    get_lr_scheduler,
)
from modules.audio import (
    FilterBankConfig,
    MelSpectrogramConfig,
    MfccConfig,
    SpectrogramConfig,
)
from modules.model import build_model
from modules.vocab import KoreanSpeechVocabulary
from modules.data import split_dataset, collate_fn
from modules.utils import Optimizer
from modules.metrics import get_metric
from modules.inference import single_infer

from torch.utils.data import DataLoader
import torch.optim as optim

def save_model(model, optimizer, path):
    state = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    torch.save(state, os.path.join(path, 'model.pt'))
    print('Model saved')

def load_model(model, optimizer, path):
    state = torch.load(os.path.join(path, 'model.pt'))
    model.load_state_dict(state['model'])
    if 'optimizer' in state and optimizer:
        optimizer.load_state_dict(state['optimizer'])
    print('Model loaded')

def infer_model(model, path):
    model.eval()
    results = []
    for i in glob(os.path.join(path, '*')):
        results.append(
            {
                'filename': i.split('/')[-1],
                'text': single_infer(model, i)[0]
            }
        )
    return sorted(results, key=lambda x: x['filename'])

def main(config):

    warnings.filterwarnings('ignore')
    
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    torch.cuda.manual_seed_all(config.seed)
    device = torch.device('cpu')
    if hasattr(config, "num_threads") and int(config.num_threads) > 0:
        torch.set_num_threads(config.num_threads)
    # labels path
    vocab = KoreanSpeechVocabulary('labels.csv', output_unit='character')
    #print(vocab)

    # print(device)
    model = build_model(config, vocab, device)
    model = model.to(device)
    # print(model)

    optimizer = get_optimizer(model, config)
    # print(optimizer)
    metric = get_metric(metric_name='CER', vocab=vocab)

    if config.mode == 'train':
        # dataset path
        DATASET_PATH = 'data'  # replace with the actual dataset path
        config.dataset_path = DATASET_PATH
        label_path = os.path.join(DATASET_PATH, 'train', 'train_label')
        # transcripts file path

        train_dataset, valid_dataset = split_dataset(config, 'transcripts-final.txt', vocab)
        
        lr_scheduler = get_lr_scheduler(config, optimizer, len(train_dataset))
        optimizer = Optimizer(optimizer, lr_scheduler, int(len(train_dataset)*config.num_epochs), config.max_grad_norm)
        criterion = get_criterion(config, vocab)

        num_epochs = config.num_epochs

        train_begin_time = time.time()

        for epoch in range(num_epochs):
            print('[INFO] Epoch %d start' % epoch) 
            train_dataset, valid_dataset = split_dataset(config, 'transcripts-final.txt', vocab)
            train_loader = DataLoader(
                train_dataset,
                batch_size=config.batch_size,
                shuffle=True,
                collate_fn=collate_fn,
                num_workers=config.num_workers
            )

            model, train_loss, train_cer = trainer(
                'train',
                config,
                train_loader,
                optimizer,
                model,
                criterion,
                metric,
                train_begin_time,
                device
            )

            print('[INFO] Epoch %d (Training) Loss %0.4f CER %0.4f' % (epoch, train_loss, train_cer))

            # valid
            valid_loader = DataLoader(
                valid_dataset,
                batch_size=config.batch_size,
                shuffle=True,
                collate_fn=collate_fn,
                num_workers=config.num_workers
            )

            model, valid_loss, valid_cer = trainer(
                'valid',
                config,
                valid_loader,
                optimizer,
                model,
                criterion,
                metric,
                train_begin_time,
                device
            )

            print('[INFO] Epoch %d (Validation) Loss %0.4f  CER %0.4f' % (epoch, valid_loss, valid_cer))

            print(f'[INFO] epoch {epoch} is done')
            
            
            # Save the checkpoint after each epoch
            checkpoint = { 
                'epoch': epoch,
                'model': model.state_dict()
            }
            torch.save(checkpoint, f'checkpoint_epoch_{epoch}.pth')
            print("model saved")
        print('[INFO] train process is done')
        torch.save(checkpoint, f'checkpoint_epoch_{epoch}.pth')
 
    elif config.mode == 'save':
        save_model(model, optimizer, "state")  # replace with the desired path
        print("model saved")
    elif config.mode == 'load':
        load_model(model, optimizer, "state")  # replace with the desired path
        print("model loaded")
    elif config.mode == 'infer':
        results = infer_model(model, "infer")  # replace with the desired path
        print(results)

if __name__ == '__main__':


    args = argparse.ArgumentParser()

    args.add_argument('--mode', type=str, default='train')
    args.add_argument('--iteration', type=str, default='0')
    args.add_argument('--pause', type=int, default=0)


    # Parameters 
    args.add_argument('--use_cuda', type=bool, default=True)
    args.add_argument('--seed', type=int, default=777)
    args.add_argument('--num_epochs', type=int, default=50)
    args.add_argument('--batch_size', type=int, default=1)
    args.add_argument('--save_result_every', type=int, default=10)
    args.add_argument('--checkpoint_every', type=int, default=1)
    args.add_argument('--print_every', type=int, default=50)
    args.add_argument('--dataset', type=str, default='kspon')
    args.add_argument('--output_unit', type=str, default='character')
    args.add_argument('--num_workers', type=int, default=8)
    args.add_argument('--num_threads', type=int, default=16)
    args.add_argument('--init_lr', type=float, default=1e-06)
    args.add_argument('--final_lr', type=float, default=1e-06)
    args.add_argument('--peak_lr', type=float, default=1e-04)
    args.add_argument('--init_lr_scale', type=float, default=1e-02)
    args.add_argument('--final_lr_scale', type=float, default=5e-02)
    args.add_argument('--max_grad_norm', type=int, default=40)
    args.add_argument('--warmup_steps', type=int, default=10)
    args.add_argument('--weight_decay', type=float, default=1e-05)
    args.add_argument('--reduction', type=str, default='mean')
    args.add_argument('--optimizer', type=str, default='adam')
    args.add_argument('--lr_scheduler', type=str, default='tri_stage_lr_scheduler')
    args.add_argument('--total_steps', type=int, default=10)

    args.add_argument('--architecture', type=str, default='deepspeech2')
    args.add_argument('--use_bidirectional', type=bool, default=True)
    args.add_argument('--dropout', type=float, default=3e-01)
    args.add_argument('--num_encoder_layers', type=int, default=3)
    args.add_argument('--hidden_dim', type=int, default=256)
    args.add_argument('--rnn_type', type=str, default='gru')
    args.add_argument('--max_len', type=int, default=40)
    args.add_argument('--activation', type=str, default='hardtanh')
    args.add_argument('--teacher_forcing_ratio', type=float, default=1.0)
    args.add_argument('--teacher_forcing_step', type=float, default=0.0)
    args.add_argument('--min_teacher_forcing_ratio', type=float, default=1.0)
    args.add_argument('--joint_ctc_attention', type=bool, default=False)

    args.add_argument('--audio_extension', type=str, default='wav')
    args.add_argument('--transform_method', type=str, default='fbank')
    args.add_argument('--feature_extract_by', type=str, default='kaldi')
    args.add_argument('--sample_rate', type=int, default=80)
    args.add_argument('--frame_length', type=int, default=20)
    args.add_argument('--frame_shift', type=int, default=10)
    args.add_argument('--n_mels', type=int, default=80)
    args.add_argument('--freq_mask_para', type=int, default=18)
    args.add_argument('--time_mask_num', type=int, default=4)
    args.add_argument('--freq_mask_num', type=int, default=2)
    args.add_argument('--normalize', type=bool, default=True)
    args.add_argument('--del_silence', type=bool, default=True)
    args.add_argument('--spec_augment', type=bool, default=True)
    args.add_argument('--input_reverse', type=bool, default=False)

    config = args.parse_args()    
    #print(config)
    main(config)

