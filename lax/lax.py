#! /usr/bin/env python3

# the folowing comments are speculative:
#numerical soulution roadmap:
#1.  first given L and A check compatebility
#2.  given U(t) find eigenfunctions and eigenvalues of Lf=\lambda f
#3.  evolve eigenfunctions forward to t+dt using A and if A depends on U(t) compute U(t+dt)
#        by solving Lf=\lambda f when \lambda and f are known.
#4.  repeat step (3) untill t=t2, then compute U(t2) and return.

import sympy
import numpy
import traceback

import lax.timeout
import lax.functions
import lax.operators

class LaxError(Exception):
    pass

class LaxPair:
    def __init__(self, L, A, constants, x, t, tout=None):
        self.L = L
        self.A = A
        self.constants = constants
        self.x = x
        self.t = t
        
        self.LAX = None
        self.PDE = None
        
        self.msg = ""
        
        if tout is None:
            tout = 0

                
        self.LAX = lax.operators.commutator(self.L, self.A)

        try:
            self.f = lax.functions.function("f", 2)(self.x, self.t)        
        except ValueError:
            raise RuntimeError('The token "f" is already in use and cannot be defined by LaxPair.')

        with lax.timeout.timeout(tout):
            LAXf = self._simplify(self.LAX(self.f).to_sympy())
            PDE = [self._simplify(LAXf.coeff(value.to_sympy())) for key, value in self.f.derived_functions().items() if "_" not in key]
            if len(PDE) == 1:
                PDE = PDE[0]
            elif len(PDE) == 0:
                PDE = 0
            else:
                raise RuntimeError("Failed to seporate the PDE from the compatibility conditions.")
            
            if (PDE == 0):
                raise LaxError("The PDE is trivially zero.")
            
            compatibility = [condition for condition in [self._simplify(LAXf.coeff(value.to_sympy())) for key, value in self.f.derived_functions().items() if "_" in key] if condition != 0]
            constants = [constant.to_sympy() for constant in self.constants]
            variables = [variable.to_sympy() for variable in [self.x, self.t]]
            
            solutions = sympy.solve(compatibility, constants, exclude=variables, dict=True)
            if isinstance(solutions, dict):
                #ensure that solutions is a list of dicts
                solutions = [solutions]
    
            solutions = [solution for solution in solutions if all([len(value.free_symbols & set(variables)) == 0 for key, value in solution.items()])]
            
            if not (all([self._simplify(condition.subs(solution)) == 0 for condition in compatibility for solution in solutions]) and len(solutions) != 0):
                raise LaxError("One or more compatibility conditions failed.")
            
            #PDE = [(self.L, self.A, equation) for equation in [self._simplify(PDE.subs(solution)) for solution in solutions] if equation != 0]
            PDE = [(self._simplify(self.L(self.f).to_sympy().subs(solution)), self._simplify(self.A(self.f).to_sympy().subs(solution)), equation) for (equation, solution) in [(self._simplify(PDE.subs(solution)), solution) for solution in solutions] if equation != 0]
            if len(PDE) == 0:
                raise LaxError("All compatible PDEs are trivially zero.")
            
        self.PDE = PDE
        self.msg = "PDEs found: [\n" + ",\n\n".join([str(P[0]) + ";\n" + str(P[1]) + ";\n" + str(P[2]) for P in self.PDE]) + "\n]"

    def get_msg(self):
        return self.msg

    def _simplify(self, expression):
        return sympy.simplify(sympy.expand(expression))
    
class GenerateLax:
    def __init__(self, fname, tout=60, autoStart=True, seed=None):
        self.tout = tout
        self.fname = fname
        self.autoStart = autoStart
        self.seed = seed
    
        self.constants = None
        self.x = None
        self.t = None
        self.u = None

        #dict of dicts {"function":function_call, "min_args":0, "max_args":20, "weight":2}
        self.operators = {}
        self.L_operator_distribution = {}
        self.A_operator_distribution = {}
        self.num_args_distribution = numpy.array([8, 4, 2, 1])

        if self.seed is None:
            numpy.random.seed()
        else:
            numpy.random.seed(self.seed)
        
        self._reset()
        
        if self.autoStart:
            self.findPairs()

    def findLaxPair(self):
        self._reset()
        with lax.timeout.timeout(self.tout):
            L = self._generateOperator(self.L_operator_distribution)
            A = self._generateOperator(self.A_operator_distribution)
        try:
            laxpair = LaxPair(L, A, self.constants, self.x, self.t, self.tout)
        except NotImplementedError:
            #still need to solve "no valid subset found" error
            raise LaxError("just a bandaid")
        return laxpair

    def findPairs(self):
        while True:
            try:
                laxpair = self.findLaxPair()
                with open(self.fname, "a") as fout:
                    fout.write(laxpair.get_msg())
            except (LaxError, TimeoutError, KeyError):
                continue

    def _generateOperator(self, distribution):
        #use sself.operators and distribution
        keys = list(self.operators.keys())
        operator_weights = [distribution[key] for key in keys]
        key_index = numpy.random.choice(len(keys), p=operator_weights/numpy.sum(operator_weights))
        operator = self.operators[keys[key_index]]
        
        try:
            operand_distribution = self.num_args_distribution[operator["min_args"]:operator["max_args"] + 1]
        except TypeError:
            operand_distribution = self.num_args_distribution[operator["min_args"]:operator["max_args"]]
        operand_options = range(operator["min_args"], operator["min_args"] + len(operand_distribution))
        num_operands = numpy.random.choice(operand_options, p=operand_distribution/numpy.sum(operand_distribution))
        
        arguments = [self._generateOperator(distribution) for _ in range(num_operands)]
        if len(arguments) > 0:
            if keys[key_index] == "constant":
                return self._new_constant()(*arguments)
            else:
                return operator["function"](*arguments)
        else:
            if keys[key_index] == "constant":
                return self._new_constant()
            else:
                return operator["function"]
    
    def _new_constant(self):
        const = lax.functions.constant("c" + str(len(self.constants) + 1))
        self.constants.append(const)
        return lax.operators.multiply(const)
        
    def _reset(self):
        lax.functions.reset()
        self.constants = []
        self.x = lax.functions.variable("x")
        self.t = lax.functions.variable("t")
        self.u = lax.functions.function("u", 2)(self.x, self.t)

        self.operators = {"add":{"function":lax.operators.add, "min_args":1, "max_args":None},
                          "commutator":{"function":lax.operators.commutator, "min_args":2, "max_args":2},
                          "multiply_u":{"function":lax.operators.multiply(self.u), "min_args":0, "max_args":1},
                          "partial_x":{"function":lax.operators.partial(self.x), "min_args":0, "max_args":1},
                          "partial_t":{"function":lax.operators.partial(self.t), "min_args":0, "max_args":1},
                          "constant":{"function":self._new_constant, "min_args":1, "max_args":1}}

        self.L_operator_distribution = {"add":1, "commutator":2, "multiply_u":4, "partial_x":5, "partial_t":0, "constant":0}
        self.A_operator_distribution = {"add":1, "commutator":2, "multiply_u":4, "partial_x":3, "partial_t":10, "constant":6}

def GenerateLaxHandler(dumpName, *args, **kwargs):
    try:
        return GenerateLax(*args, **kwargs)
    except KeyboardInterrupt:
        pass
    except Exception as E:
        with open(dumpName, "w") as fout:
            fout.write(traceback.format_exc())
