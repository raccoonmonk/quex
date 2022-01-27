# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.blackboard import Lng

class Bisection(object):
    __slots__ = ("bisection_value", "low", "high")

    def __init__(self, BisectionValue, Low, High):
        """TM -- transition map
           MOAT -- Most Often Appearing Target
        """
        self.bisection_value = BisectionValue
        self.low             = Low
        self.high            = High

    def implement(self):
        txt = [
            Lng.IF_INPUT("<", self.bisection_value)
        ]
        txt.extend(
            self.low.implement()
        )
        txt.append("%s\n" % Lng.ELSE_FOLLOWS)
        txt.extend(
            self.high.implement()
        )
        txt.append(
            "%s\n" % Lng.END_IF
        )
        return txt
