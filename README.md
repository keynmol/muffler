# muffler
This tool was born out of lack of understanding of Spark's performance tuning. Instead of trying to understand, what chapters of the tuning guide apply to my particular application, I decided to try all approaches at once and try to find out the best set of parameters.

I also wanted it to be slightly more flexible than 7 for-loops folded into each other.

## usage

What I wanted is to have two things - a **command** that I can run in shell which has arguments **formatted** in a way expected by the application, and a list of **parameters** that correspond to those arguments with values **transformed** in a way suitable for my analysis.

For example, `spark-submit` expects values like `--executor-memory 256M` or `--executor-memory 1G`, but for analysis I'd rather convert both to values `0.256` and `1` respectively. 

Each option has a `format` function which converts key/value pairs into command line arguments. For example `("executor-memory", "3G") => "--executor-memory 3G"`. It can also have functions that transform key/value pairs into a format you can use in reporting, i.e. name `"executor-memory" becomes `"executor memory (GB)"`, value `"3G"` becomes `3` and `"256M"` becomes `256` 

Here's my example. After defining a few classes(for convenience, really), we can do this:

```python
import muffler as mf

# not how we dont mention all the subclasses, but only their superclasses
# the rest is taken care of
cmd_template = ("~/spark{sparkVersion}/bin/spark-submit {SparkSubmitOption} "
                "{SparkConfOption} app.jar {ProgramOption}")

options = []
options.append(SparkSubmitThreadsOption("master", ["2", "4"]))
options.append(SparkSubmitMemOption("executor-memory", ["1G", "3G"]))
options.append(SparkConfOption("spark.shuffle.memoryFraction", [0.6, 0.8]))
options.append(SizeOption("d", ["100", "500", "1000"]))
options.append(mf.Quiet("Run", range(2))) # Quiet is not an option, just means that each command will be ran twice
options.append(mf.Placeholder("sparkVersion", ["1.3.1", "1.4.0"])) # Placeholder can be used by the name right in the command

fieldnames = mf.parameters_names(options)
for parameters, command in mf.parametrize(options, cmd_template):
    print("Parameters: " + str(parameters))
    print("Command: " + command +"\n")
```

And it will output(note the transformed names and values for parameters):

```
Parameters: {'Run': 0, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '100', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_100.jsonl

Parameters: {'Run': 1, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '100', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_100.jsonl

Parameters: {'Run': 0, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '500', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_500.jsonl

Parameters: {'Run': 1, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '500', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_500.jsonl

Parameters: {'Run': 0, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '1000', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_1000.jsonl

Parameters: {'Run': 1, 'spark.shuffle.memoryFraction': 0.6, 'input_size': '1000', 'threads': '2', 'executor-memory(GB)': '1'}
Command: spark-submit --master local[2] --executor-memory 1G --conf spark.shuffle.memoryFraction=0.6 app.jar -d input_1000.jsonl

... etc ...
```

The dictionary of parameters is great to use in conjunction with `csv`'s `DictWriter`:

```python
fieldnames = mf.parameters_names(options)
with open("output.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames+["Time"])
    writer.writeheader()

    for parameters, command in mf.parametrize(options, cmd_template):
        before = time.time()
        os.system(command)
        elapsed = time.time() - before
        parameters.update({"Time": elapsed})
        writer.writerow(parameters)
```

Here are the classes for options:

```python
import muffler as mf

# i.e. --conf spark.serializer=org.apache.spark.serializer.KryoSerializer
class SparkConfOption(mf.Option):

    def format(self, value):
        return "--conf {0}={1}".format(self.name, value)

# i.e. --name App1
class SparkSubmitOption(mf.Option):

    def format(self, value):
        return "--{0} {1}".format(self.name, value)

# here we use re-formatting
# --master local[4]
class SparkSubmitThreadsOption(SparkSubmitOption):

    def format(self, value):
        return "--{0} local[{1}]".format(self.name, value)

    def transform_name(self):
        return "threads"

# this transforms value before returning it to the script
# converting it to gigabytes
# and also transforms the name
class SparkSubmitMemOption(SparkSubmitOption):

    def transform_value(self, value):
        if "G" in value:
            return value[0:-1]
        elif "M" in value:
            return str(float(value[0:-1]) / 1024)

    def transform_name(self):
        return self.name + "(GB)"


# just a dummy class
class ProgramOption(mf.Option):
    pass

# something I would use to control the running time growth
# depending on input size
class SizeOption(ProgramOption):

    def format(self, value):
        return "-{0} input_{1}.jsonl".format(self.name, value)

    def transform_name(self):
        return "input_size"
```
