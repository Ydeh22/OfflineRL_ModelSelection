#!/bin/bash


#SBATCH --job-name=WISAMmix
#SBATCH --mail-user=tangsp@umich.edu 
#SBATCH --mail-type=BEGIN,END
#SBATCH --cpus-per-task=4
#SBATCH --nodes=1
#SBATCH --mem-per-cpu=4GB
#SBATCH -p standard
#SBATCH --time=144:00:00
#execute code


N=$1
name=$2
run=$3

python run-WIS-AM-models-behavior-mixed.py --input_dir='../datagen/unif-100k/' --output_dir="./output/run$run/unif-10k/" --N=10000 --split='va' --run=$run --va_split_name='va10k_mixed'
