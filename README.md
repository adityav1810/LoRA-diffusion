# CS7180-FinalProject

This is the submission for 

The Final Project
for the course "CS7180 Advanced Perception"
The link for this repo - https://github.khoury.northeastern.edu/anirudhmuthu/CS7180-FinalProject

13th December 2023

---------------------------------------------
Details

## Repository Highlights

- Project Report - "cs7180-AnirudhGuganAditya-FinalProject.pdf"
- Presentation - "CS7180-FinalProject-Presentation.pdf"
- Presentation Video Link - https://drive.google.com/file/d/1-Q1rFYcKoLLUWeFGq7emhFF3-wyjemnw/view?usp=sharing
- Demo Notebook- "training_exp.ipynb"
- Source Code - in the files and folders inside ./src/

## Authors
- Anirudh Muthuswamy, NUID - 002783250
- Gugan Kathiresan, NUID -002756523
- Aditya Shanmugham, NUID - 002724777

## Operating System
- Google Colab Pro Ubuntu / T4 GPU
- Discovery Cluster Jupyter Notebook / V100 GPU
- macOS for file management

## Required Packages
In your command line
> cd /path/to/your/project
> pip install -r requirements.txt

## Compilation Instructions for the script files
- Download the datasets
    - FloodNet dataset - https://drive.google.com/drive/folders/1sZZMJkbqJNbHgebKvHzcXYZHJd6ss4tH?usp=sharing
    - Set5 dataset - https://uofi.box.com/shared/static/kfahv87nfe8ax910l85dksyl2q212voc.zip
    - Set14 dataset - https://uofi.box.com/shared/static/igsnfieh4lz68l926l8xbklwsnnk8we9.zip

- Unzip the files and place it in the working directory
- Install all requirements from the "requirements.txt" file
- Open src/main.py and edit the parameters according to your experiment's requirments. These include parameters like dataset_path, crop_size, batch_size, warmup_batches, n_batches, batch, sample_interval, save_path_suffix,and lora_save_path
- Then simply run tthe main.py file sing 
> !python ./src/main.py


## Time Travel Days
- None Used

