from collections import defaultdict


class Option:

    def __init__(self, name, values):
        self.name = name
        self.values = values

    def transform_value(self, value):
        return value

    def transform_name(self):
        return self.name

    def class_name(self):
        return self.__class__.__name__

    def format(self, value):
        ""

    def joiner(self):
        return " "

    def classes():
        stack = [Option]
        aliases = defaultdict(list)
        while len(stack) > 0:
            start = stack.pop()
            for s in start.__subclasses__():
                aliases[s.__name__].append(start.__name__)
                stack.append(s)

        return aliases

    def closure(aliases):
        def lock_closure(name, aliases):
            stack = [name]
            result = [name]
            while len(stack) > 0:
                start = stack.pop()
                if start in aliases:
                    unexplored = [x for x in aliases[start] if x not in result]
                    result += unexplored
                    stack += unexplored

            return result

        return dict((k, lock_closure(k, aliases)) for k in aliases.keys())


class Quiet(Option):

    def format(self, value):
        return ""


class Placeholder(Option):

    def format(self, value):
        return value


def parameters_names(options):
    return [opt.transform_name() for opt in options]


def parametrize(options, command_template, progress=True):
    def combinations(options):
        if len(options) == 0:
            return []

        opt = options[0]
        results = []
        if len(options) > 1:
            for value in opt.values:
                ahead = combinations(options[1:len(options)])
                results += [([(opt, value)] + x) for x in ahead]
        else:
            results = [[(opt, value)] for value in opt.values]

        return results

    classes_mapping = Option.closure(Option.classes())

    all_combinations = combinations(options)
    num_combinations = len(all_combinations)

    joiners = {'Option': " "}
    i = 0
    for combination in all_combinations:
        args = defaultdict(list)
        parameters = {}
        value_options = {}
        for (option, value) in combination:
            joiners[option.__class__.__name__] = option.joiner()

            classes = classes_mapping[option.class_name()]
            if "Placeholder" in classes:
                value_options[option.name] = option.format(value)
            else:
                for class_name in classes:
                    if value:
                        args[class_name].append(option.format(value))
                    else:
                        args[class_name].append(None)

            parameters[option.transform_name()] = option.transform_value(value)

        def get_joiner(k):
            if k in joiners:
                return joiners[k]
            candidates = classes_mapping[k]
            for c in candidates:
                if c in joiners:
                    return joiners[c]

        args = dict((k, get_joiner(k).join(a for a in v if a is not None))
                    for k, v in args.items())
        args.update(value_options)
        i += 1
        if progress:
            yield (parameters, command_template.format(**args), i, num_combinations)
        else:
            yield (parameters, command_template.format(**args))
