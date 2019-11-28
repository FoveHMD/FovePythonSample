# Examples for Python bindings for FoveAPI

## Setting up python environment

To use the Python bindings for FoveAPI, one needs an instance of python runtime
your system, and have Fove python bindings in the `PYTHONPATH` environment variable.

On Windows, we assume that the samples will be run using `cmd.exe`.
(If you prefer to use a Python IDE, please refer to the manual of the IDE
for propely setting up a `python` executable, `PYTHONPATH`etc.)

Firstly, make sure that a version of `python` is installed and available.
On `cmd.exe`:
```
> python
Python 3.7.5 (default, Oct 14 2019, 23:08:55)
>>> print("Hello, Fove!")
Hello, Fove!
>>> 1 + 1
2
```
Although the Fove Python bindings are supposed to work both for python versions
`2.x` and `3.x`, we strongly recommend the users to use version `3.x`, unless
there are strong reasons not to.

If the Fove SDK has been installed to `C:\path\to\FoveSDK`, python bindings
would be located at `C:\path\to\FoveSDK\python\site-packages\fove`.
So the `PYTHONPATH` environment variable for an instance of `cmd.exe` should be
set as follows:
```
> set PYTHONPATH="C:\path\to\FoveSDK\python\site-packages\fove";%PYTHONPATH%
```
Then, from the same `cmd.exe`, you should be able to run `sample.py` (provided
that the file is in the current directory; `cd` (change directory) if not):
```
> cd /pass/to/sample_py/
> dir
sample.py
> python sample.py
..
```
