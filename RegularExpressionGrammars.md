## Introduction ##

The [regex2wfst.py](http://code.google.com/p/transducersaurus/source/browse/python/regex2wfst.py) tool supports a modestly flexible regular expression like syntax.  This is not as macro-rich as standard Java Speech Grammar Format, but does support the full range of regular grammars.


## Details ##

The supported operations and corresponding operator tokens are described below:
  * **`*`** - star operator, 'zero or more' occurrences.
  * **+** - plus operator, 'one or more' occurrences.
  * **?** - question mark, 'zero or one' occurrence.
  * **|** - branch or alternate, 'either or'.
  * **(**, **)** - parentheses, used to enclose alternates
  * **`[`**, **`]`** - square brackets, used to enclose weights

## Examples ##
Word tokens in a regular expression grammar should be separated by at least one whitespace character.  Multiple whitespaces will be ignored.  Operator tokens do not need to be separated by whitespace.  Weights must be enclosed in square brackets.

  * `<s>  THIS+    IS ?   A (TEST [5.5]|(LOT OF)+ FUND [-.123]*)</s>`
<img src='http://www.gavo.t.u-tokyo.ac.jp/~novakj/gram1-opt.png' />
  * `<s>  I (LIKE|HATE) (SUSHI[0.2]|STEAK[0.4]|YAKINIKU[0.4]+)</s>`
<img src='http://www.gavo.t.u-tokyo.ac.jp/~novakj/gram2-opt.png' />
  * JSGF-style grammar specifications are also supported.  In these definitions the following rules apply:
    * A top-level grammar with variable name '$GRAMMAR' must be defined
    * Subexpression variable names must conform to the regular expression ` /^\$[a-zA-Z0-9_\-\.$/ `, that is, a dollar sign followed by one or more ASCII characters, digits, underscores, dashes and periods.
    * Each subexpression must consist of a valid subexpression variable name, a separator of the form '::=', and a valid regular expression grammar.
    * Any switch/alternate expressions must be enclosed in parentheses
    * Thus, a valid JSGF definition for the preceding example might take the form,
```
$ more grammar.txt
$FOODS    ::= ( SUSHI [0.2]| STEAK[0.2]| YAKINIKU[0.4]+ )
$PREF     ::= ( LIKE | HATE )
$GRAMMAR  ::= <s> I $PREF $FOODS </s>
```
  * Invalid example 1:
    * Top-level $GRAMMAR variable is not defined,
```
$ more grammar.txt
$FOODS    ::= ( SUSHI [0.2]| STEAK[0.2]| YAKINIKU[0.4]+ )
$PREF     ::= <s> I ( LIKE | HATE ) $FOODS </s>
```
    * Subexpression variable name '$PR=EF' is not valid,
```
$ more grammar.txt
$FOODS    ::= ( SUSHI [0.2]| STEAK[0.2]| YAKINIKU[0.4]+ )
$PR=EF    ::= ( LIKE | HATE )
$GRAMMAR  ::= <s> I $PREF $FOODS </s>
```
    * Missing separator '::=',
```
$ more grammar.txt
$FOODS    ::= ( SUSHI [0.2]| STEAK[0.2]| YAKINIKU[0.4]+ )
$PREF     ( LIKE | HATE )
$GRAMMAR  ::= <s> I $PREF $FOODS </s>
```