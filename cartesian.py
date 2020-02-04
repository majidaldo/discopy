# -*- coding: utf-8 -*-
"""
Implements the PRO of functions on tuples with cartesian product as tensor.

We have access to Swap, Copy and Discard maps, generated by:

>>> COPY = Box('copy', 1, 2, lambda *x: x + x)
>>> SWAP = Box('swap', 2, 2, lambda x, y: (y, x))
>>> DISCARD = Box('discard', 1, 0, lambda *x: ())
>>> assert Swap(1, 2) == SWAP @ Id(1) >> Id(1) @ SWAP
>>> assert Discard(2) == DISCARD @ DISCARD
>>> assert Copy(3) == COPY @ COPY @ COPY >> Id(1) @ SWAP @ SWAP @ Id(1)
...                                      >> Id(2) @ SWAP @ Id(2)

The call method for diagrams of functions is implemented using PythonFunctors.

We can check naturality of the Swap on specific inputs:

>>> f = disco(2, 2)(lambda x, y: (x + 1, y - 1))
>>> g = disco(2, 2)(lambda x, y: (2 * x, 3 * y))
>>> assert (f @ g >> Swap(2, 2))(42, 43, 44, 45)\\
...     == (Swap(2, 2) >> g @ f)(42, 43, 44, 45)

As well as the Yang-Baxter equation:

>>> assert (SWAP @ Id(1) >> Id(1) @ SWAP >> SWAP @ Id(1))(41, 42, 43)\\
...     == (Id(1) @ SWAP >> SWAP @ Id(1) >> Id(1) @ SWAP)(41, 42, 43)

We can check the axioms for the Copy/Discard comonoid on specific inputs:

>>> assert (f >> Copy(2))(42, 43) == (Copy(2) >> f @ f)(42, 43)
>>> assert (Copy(3) >> Id(3) @ Discard(3))(42, 43, 44) == Id(3)(42, 43, 44)\\
...     == (Copy(3) >> Discard(3) @ Id(3))(42, 43, 44)
>>> assert (Copy(4) >> Swap(4, 4))(42, 43, 44, 45) == Copy(4)(42, 43, 44, 45)
"""

from discopy.cat import AxiomError
from discopy import messages, rigidcat
from discopy.cat import Quiver
from discopy.rigidcat import PRO, RigidFunctor


def tuplify(xs):
    return xs if isinstance(xs, tuple) else (xs, )


def untuplify(*xs):
    return xs[0] if len(xs) == 1 else xs


class Function(rigidcat.Box):
    """
    Wraps python functions with domain and codomain information.

    Parameters
    ----------
    dom : int
        Domain of the diagram.
    cod : int
        Codomain of the diagram.
    function: any
        Python function with a call method.

    >>> sort = Function(3, 3, lambda *xs: tuple(sorted(xs)))
    >>> swap = Function(2, 2, lambda x, y: (y, x))
    >>> assert (sort >> Function.id(1) @ swap)(3, 2, 1) == (1, 3, 2)
    """
    def __init__(self, dom, cod, function):
        self._function = function
        super().__init__(repr(function), PRO(dom), PRO(cod))

    @property
    def function(self):
        """
        The function stored in a discopy.Function object is immutable

        >>> f = Function(2, 2, lambda x: x)
        >>> f.function = lambda x: 2*x  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        AttributeError: can't set attribute
        """
        return self._function

    def __repr__(self):
        return "Function(dom={}, cod={}, function={})".format(
            self.dom, self.cod, repr(self.function))

    def __str__(self):
        return repr(self)

    def __call__(self, *values):
        """
        In order to call a Function, it is sufficient that the input
        has a length which agrees with the domain dimension.

        Parameters
        ----------
        values : tuple
        """
        if not len(values) == len(self.dom):
            raise AxiomError("Expected input of length {}, got {} instead."
                             .format(len(self.dom), len(values)))
        return self.function(*values)

    def then(self, other):
        """
        Returns the sequential composition of 'self' with 'other'.

        >>> copy = Function(1, 2, lambda *x: x + x)
        >>> swap = Function(2, 2, lambda x, y: (y, x))
        >>> assert (copy >> swap)(1) == copy(1)
        >>> assert (swap >> swap)(1, 2) == (1, 2)
        """
        if not isinstance(other, Function):
            raise TypeError(messages.type_err(Function, other))
        if len(self.cod) != len(other.dom):
            raise AxiomError("{} does not compose with {}."
                             .format(repr(self), repr(other)))
        return Function(self.dom, other.cod,
                        lambda *vals: other(*tuplify(self(*vals))))

    def tensor(self, other):
        """
        Returns the parallel composition of 'self' and 'other'.

        >>> copy = Function(1, 2, lambda *x: x + x)
        >>> swap = Function(2, 2, lambda x, y: (y, x))
        >>> assert (swap @ swap)(1, 2, 3, 4) == (2, 1, 4, 3)
        >>> assert (copy @ copy)(1, 2) == (1, 1, 2, 2)
        """
        if not isinstance(other, Function):
            raise TypeError(messages.type_err(Function, other))
        dom, cod = self.dom @ other.dom, self.cod @ other.cod

        def product(*vals):
            vals0 = tuplify(self(*vals[:len(self.dom)]))
            vals1 = tuplify(other(*vals[len(self.dom):]))
            return untuplify(*(vals0 + vals1))
        return Function(dom, cod, product)

    @staticmethod
    def id(dom):
        """
        >>> assert Function.id(0)() == ()
        >>> assert Function.id(2)(1, 2) == (1, 2)
        >>> Function.id(1)(1, 2)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        discopy.cat.AxiomError: Expected input of length 1, got 2 instead.
        """
        return Function(dom, dom, untuplify)


class PythonFunctor(RigidFunctor):
    """
    Implements functors into the category of Python functions on tuples
    """
    def __init__(self, ob, ar):
        super().__init__(ob, ar, ob_cls=PRO, ar_cls=Function)


class Diagram(rigidcat.Diagram):
    """
    Implements diagrams of Python functions.
    """
    def __init__(self, dom, cod, boxes, offsets, layers=None):
        super().__init__(PRO(dom), PRO(cod), boxes, offsets, layers=layers)

    @staticmethod
    def _upgrade(diagram):
        """
        Takes a rigidcat.Diagram and returns a cartesian.Diagram.
        """
        return Diagram(len(diagram.dom), len(diagram.cod),
                       diagram.boxes, diagram.offsets, layers=diagram.layers)

    @staticmethod
    def id(x):
        """
        >>> Diagram.id(2)
        Id(2)
        """
        return Id(x)

    def __call__(self, *values):
        """
        >>> assert SWAP(1, 2) == (2, 1)
        >>> assert (COPY @ COPY >> Id(1) @ SWAP @ Id(1))(1, 2) == (1, 2, 1, 2)
        """
        ob = Quiver(lambda t: PRO(len(t)))
        ar = Quiver(lambda f:
                    Function(len(f.dom), len(f.cod), f.function))
        return PythonFunctor(ob, ar)(self)(*values)


class Id(Diagram):
    """
    Implements identity diagrams on dom inputs.

    >>> c =  SWAP >> ADD >> COPY
    >>> assert Id(2) >> c == c == c >> Id(2)
    """
    def __init__(self, dom):
        """
        >>> assert Diagram.id(42) == Id(42) == Diagram(42, 42, [], [])
        """
        super().__init__(PRO(dom), PRO(dom), [], [], layers=None)

    def __repr__(self):
        """
        >>> Id(42)
        Id(42)
        """
        return "Id({})".format(len(self.dom))

    def __str__(self):
        """
        >>> print(Id(42))
        Id(42)
        """
        return repr(self)


class Box(rigidcat.Box, Diagram):
    """
    Implements Python functions as boxes in a learner.Diagram.
    """
    def __init__(self, name, dom, cod, function=None, data=None):
        """
        >>> assert COPY.dom == PRO(1)
        >>> assert COPY.cod == PRO(2)
        """
        if function is not None:
            self._function = function
        rigidcat.Box.__init__(self, name, PRO(dom), PRO(cod), data=data)
        Diagram.__init__(self, dom, cod, [self], [0])

    @property
    def function(self):
        return self._function

    def __repr__(self):
        return "Box({}, {}, {}{}{})".format(
            repr(self.name), len(self.dom), len(self.cod),
            ', function=' + repr(self.function) if self.function else '',
            ', data=' + repr(self.data) if self.data else '')


class Swap(Diagram):
    """
    Implements the Swap map from 'left @ right' to 'right @ left'

    >>> assert Swap(2, 3)(0, 1, 2, 3, 4) == (2, 3, 4, 0, 1)
    """
    def __init__(self, left, right):
        dom, cod = PRO(left) @ PRO(right), PRO(right) @ PRO(left)
        boxes = [SWAP for i in range(left) for j in range(right)]
        offsets = [left + i - 1 - j for j in range(left) for i in range(right)]
        super().__init__(dom, cod, boxes, offsets)


class Copy(Diagram):
    """
    Implements the Copy map from 'dom' to '2 * dom'.

    >>> assert Copy(3)(0, 1, 2) == (0, 1, 2, 0, 1, 2)
    """
    def __init__(self, dom):
        result = Id(0)
        for i in range(dom):
            result = result @ COPY
        for i in range(1, dom):
            swaps = Id(0)
            for j in range(dom - i):
                swaps = swaps @ SWAP
            result = result >> Id(i) @ swaps @ Id(i)
        super().__init__(dom, 2 * dom, result.boxes, result.offsets,
                         layers=result.layers)


class Discard(Diagram):
    """
    assert Discard(3)(0, 1, 2) == () == Discard(2)(43, 44)
    """
    def __init__(dom):
        result = Id(0)
        for i in range(dom):
            result = result @ DISCARD
        super().__init__(result.dom, result.cod, result.boxes, result.offsets,
                         layers=result.layers)


class CartesianFunctor(RigidFunctor):
    """
    Implements functors into the category of Python functions on tuples.

    >>> x = rigidcat.Ty('x')
    >>> f, g = rigidcat.Box('f', x, x @ x), rigidcat.Box('g', x @ x, x)
    >>> ob = {x: PRO(1)}
    >>> ar = {f: COPY, g: ADD}
    >>> F = CartesianFunctor(ob, ar)
    >>> assert F(f >> g)(43) == 86
    """
    def __init__(self, ob, ar):
        super().__init__(ob, ar, ob_cls=PRO, ar_cls=Diagram)


def disco(dom, cod, name=None):
    """
    Decorator turning a python function into a cartesian.Box storing it,
    given domain and codomain information.

    >>> @disco(2, 1)
    ... def add(x, y):
    ...     return (x + y,)
    >>> assert isinstance(add, Box)
    >>> copy = disco(1, 2, name='copy')(lambda x: (x, x))
    """
    def decorator(func):
        if name is None:
            return Box(func.__name__, dom, cod, func)
        return Box(name, dom, cod, func)
    return decorator


COPY = Box('copy', 1, 2, lambda *x: x + x)
SWAP = Box('swap', 2, 2, lambda x, y: (y, x))
DISCARD = Box('discard', 1, 0, lambda *x: ())
ADD = Box('add', 2, 1, lambda x, y: x + y)
