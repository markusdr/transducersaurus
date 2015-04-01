The transducersaurus.py tool implements a simple domain specific language suitable for specifying WFST cascade construction algorithms.  A brief description of the grammar is listed below.
A more in-depth tutorial is on the way.

```
WFST Cascade Grammar description:

Examples: 
    CLGT cascade using static lookahead composition:
          (C*det(L)).(G*T)
    CLG cascade using standard composition, one call to determinize:
          C*det(L*G)
    CLGT cascade with final minimization and determinization:
          min(det((C*det(L)).(G*T)))
    CLGT cascade with final minimization and determinization, minimization will be performed with label-encoding:
          min[labels](det((C*det(L)).(G*T)))
    HCLGT cascade with final determinization and pushing, pushing will be performed in the log semiring, 
      with label-encoding, the first call to determinize will be performed in 
      the log semiring, using weight-encoding:
          push[log,labels](det(min(H*(det((C*det_lw(L)).(G*T))))))
          
The WFST compilation DSL supports the following WFST components:
  * H - HMM level transducer (Sphinx format only)
  * C - Context-dependencty transducer (Sphinx or HTK)
  * L - Lexicon transducer (Sphinx or HTK)
  * G - Grammar, ARPA format stochastic langauge models
  * T - Silence class transducer
  
Operations:
  * rmeps:  Epsilon removal.
  * push:   Pushing.
  * det:    Determinize
  * min:    Minimize
  * '*':    Composition
  * '.':    Static lookahead composition

The default semiring can be overridden  for 'push', 'det', and 'min' in one of two ways:
  * shorthand:
     - det_l  (log semiring)
     - det_t  (tropical semiring)
  * brackets:
     - det[log]  (log semiring)
     - det[tropical|trop|standard]  (tropical semiring)

It is also possible to specify label and/or weight encoding for the 'push', 'det', and 'min' operations:
  * shorthand, using 'min' as an example:
     - min_w  (encode weights)
     - min_s  (encode labels)
     - min_ws/min_sw  (encode weights AND labels)
  * brackets:
     - min[weights|ew,labels|el]  (encode weights AND labels)

These can be combined as well:
  * min[weights,labels,log]

Redundant specifications will be ignored:
  * min_w[weights,labels] -> min_wl

Conflicts will raise an error:
  * push[log,trop] -> "Pick a semiring!"

Unbalanced parentheses will be caught:
  * (C*det(L).(G*T) -> "Unbalanced parentheses!"
```