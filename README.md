# Baseball

A recreation of the [Baseball](https://dl.acm.org/doi/10.1145/1460690.1460714)
automatic question-answerer. There are some slight deviations from the original
paper and it uses the modern spaCy NLP library to perform POS tagging and phrase
extraction rather than the traditional methods at that time.

## Running

To run, you'll need to run the two following commands with the first one used to
extract the data for the chat script (note: you'll need to first install spaCy).

```
python3 chat.py
```
