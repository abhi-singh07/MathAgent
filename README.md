# MathAgent: Multi-Agent Framework to Tackle Challenging Math Problems with LLM


## Setup
- Set up env
```
conda env create -f environment.yml
```
- A valid key that can use GROQ needs to be put in `GROQ_API_KEY`.
- If the prompt involves wolfram, an wolfram app_id is needed.
- Customized prompt to use Python or Wolfram can be put in `prompt.py` to be tested.

## Architecture

![image](https://github.com/user-attachments/assets/df7d731d-563e-4d1a-8505-936050807626)


## Run MathAgent
- Use `--categories` to select category to run, and `--samples_per_category` for number of samples. The problems are randomly selected from level-5 difficulty. 
    
    ID : Category Name      
    0 : Algebra     
    1 : Counting & Probability     
    2 : Geometry    
    3 : Intermediate Algebra     
    4 : Number Theory    
    5 : Prealgebra    
    6 : Precalculus    
    
- Test on one level-5 problem from each category (except geometry):
```python
python main.py -ptype default --folder ./default --categories 0 1 3 4 5 6 --samples_per_category 1
```
Note: `default` is the default prompt for MathChat, other choices are `v3.9python` and `two_tools`.


- Test on all problems from each category (except geometry):
```python
python main.py -ptype default --folder ./default --categories 0 1 3 4 5 6 --samples_per_category 400
```

## Main Results

Accuracy on all the problems with difficulty level-5 from different categories of the MATH dataset with different methods.
|                     | Algebra | C.Prob | I.Alg | N.Theory | Prealg | Precalc |
|---------------------|---------|--------|-------|----------|--------|---------|
| **MathAgent (Ours) | **92.00%**  | **88.00%** | **96.00%** | **96.00%**   | **80.00%** | **76.00%**  |
| MathChat w/ Python | 52.00%  | 38.00% | 14.00% | 44.00%   | 62.00% | 26.00%  |
| MathChat w/ Tools  | 66.00% | 44.00% | 12.00% | 54.00%   | 58.00% | 20.00%  |
| MathChat w/ DeepSeek | **92.00%**  | 80.00% | 84.00% | **96.00%**   | 76.00% | **76.00%**  |


