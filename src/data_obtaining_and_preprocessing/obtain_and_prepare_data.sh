#!/bin/bash

python data_obtaining_and_preprocessing/download_original_data.py

python data_obtaining_and_preprocessing/separate_grid.py \
    --input_dir ../data/data_original \
    --output_dir ../data/data_separated_grid

python data_obtaining_and_preprocessing/convert_validation_dataset_to_train_format.py \
    --dataset_path ../data/data_separated_grid/valid.jsonl \
    --ref_path ../data/data_original/valid.ref \
    --out_path ../data/data_separated_grid/valid.jsonl \
    --total 10000

cp ../data/data_original/voc.txt ../data/data_separated_grid/voc.txt

python data_obtaining_and_preprocessing/fix_grids.py \
    -i ../data/data_separated_grid/gridname_to_grid.json \
    -o ../data/data_separated_grid/gridname_to_grid__fixed.json

python data_obtaining_and_preprocessing/filter_dataset.py \
    --dataset_path ../data/data_separated_grid/train.jsonl \
    --grids_path ../data/data_separated_grid/gridname_to_grid.json \
    --output_path ../data/data_separated_grid/train.jsonl \
    --log_dir ../data/errors_in_original_data_swipes
