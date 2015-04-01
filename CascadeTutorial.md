**As of 2011-05-10 this page has been deprecated**.  The bash scripts are no longer supported and will be removed in a future version. The 'transducersaurus.py' tool should be used instead.  And hopefully I'll get around to a tutorial for that soon.

# Introduction #

This tutorial focuses on pragmatic essentials: what an enthusiastic student should know about the component models that make up a typical ASR cascade.  These components include a language model or grammar (**G**), a pronunciation dictionary or lexicon (**L**), and a context-dependency transducer (**C**).  Depending on the particular implementation the cascade may also employ a class-based silence model (**T**).  Each of these models will be explained and illustrated in the sections below, using the tools from this project.  In the course of the final step we will construct a full, integrated cascade from the constituent models which you can plug into the Juicer WFST decoder to recognize sequences of the words 'foo' and 'bar'.

The [README.txt](http://code.google.com/p/transducersaurus/source/browse/prototypes/README.txt) file in the [prototypes](http://code.google.com/p/transducersaurus/source/browse/#hg%2Fprototypes) directory also contains a tutorial which builds a 5000 word vocabulary bigram-based cascade from a subset of the Wallstreet Journal corpus.  This tutorial focuses on an even smaller example in order to facilitate visualizations.

## Requirements ##
In order to follow along you should probably have the project installed, as well as [OpenFST](http://www.openfst.org).  If you would also like to build the graphs you should install the [Graphviz](http://www.graphviz.org/) library.  If you want to train the 'language model' yourself, I recommend installing the [mitlm](http://code.google.com/p/mitlm/) language modeling toolkit.  If you want to run the examples you will need to download and install the [Juicer](http://juicer.amiproject.org/juicer/) WFST decoder.  Juicer can be very challenging to compile.  In my experience it will not build on MacOSX 10.6, nor will it build under 64bit linux without significant modifications.  Compiling Juicer is beyond the scope of this tutorial, but there is an excellent explanation of the build process to be found here:

http://nsh.nexiwave.com/2010/05/speech-decoding-engines-part-1-juicer.html

## Further reading ##
Recommended reading for more in-depth study can be found at the end of the tutorial.

# WFST-based ASR #

Speech Recognition approaches based on Weighted Finite-State Transducers (WFST) have gained considerable popularity in recent years. The WFST approach provides an elegant, unified mathematical framework suitable for representing, building, combining and optimizing a wide variety of component knowledge sources, making it an appealing choice for the construction of integrated ASR models.

The approach was pioneered by Mohri et. al., at AT&T in the 90s.  Since then it has steadily gained momentum, and today is the subject of considerable research attention. Large industry players including Google and AT&T currently leverage the WFST approach as the basis for their commercial speech recognition technology.

The following sections describe the construction of typical silence class (**T**), Grammar (**G**), Lexicon (**L**), and Context-dependency (**C**) transducers in turn.  The tutorial closes with a description of how to compile the components into a functional cascade with the tools in this project.

## Basic knowledge sources ##
Building a working ASR cascade first requires a couple of basic knowledge sources.  These include a training corpus,

foobar.corpus
```
foo bar foo foo bar
foo foo
bar foo bar
```

a pronunciation dictionary,

foobar.dic
```
<s>     sil
</s>    sil
<sil>   sil
foo     f uw
bar     b ah r
bar     f uw
```

and in this case an HTK format acoustic model along with its associated tiedlist.  You can download examples of these last two from,

[hmmdefs.gz](http://www.gavo.t.u-tokyo.ac.jp/~novakj/hmmdefs.gz) (100mb)

[tiedlist.gz](http://www.gavo.t.u-tokyo.ac.jp/~novakj/tiedlist.gz) (tiny)

## Silence class model (T) ##

In most traditional ASR decoders such as HDecode, HVite, or Sphinx, silence modeling is handled implicitly by the decoder.  In the case of WFST decoders however, this as well as most other details are left to the user or developer and must be incorporated directly into the recognition cascade.

The [silclass2fst.py](http://code.google.com/p/transducersaurus/source/browse/prototypes/silclass2fst.py) tool can be used to create a class-based transducer from an input vocabulary list,

foobar.wordlist
```
<s>
</s>
foo
bar
```

We can build the silence class transducer with the following command,
```
$ ./silclass2fst.py foobar.wordlist foobar > foobar.t.fst.txt
```

and compile it into a graph with,
```
$ fstcompile --arc_type=log --isymbols=foobar.t.isyms --osymbols=foobar.t.osyms foobar.t.fst.txt | \
     fstdraw --portrait=true --isymbols=foobar.t.isyms --osymbols=foobar.t.osyms | \
     dot -Tpdf > foobar.t.pdf
```

which should produce something like the following:

<img src='http://i.imgur.com/FAgsq.png' width='400' />

The basic idea behind the silence class model is that it encodes an outgoing arc for each word in the vocabulary, followed by an optional, weighted loop labeled with an output silence token, and an optional weighted exit arc labeled with the epsilon symbol on both sides.  When we compose this with a grammar or language model such as that described in the next section, the result is an augmented model which potentially allows for lengthy pauses between words, even if this behavior was not encoded into the original language model.

In this case the weights on the arcs correspond to an 11% probability that a word is followed by a silence token, and a 89% probability that it is not.  These particular values were estimated from approximately 400 hours of training data from the Fisher corpus, however shifting them up or down a few percent in either direction would likely make little difference.

## Grammar model **G** ##
The grammar typically takes the form of a standard N-gram model, however in some cases an 'expert' network grammar may be employed.  In this tutorial we will focus on the N-gram case.

There are several approaches to converting an N-gram model to an equivalent WFST or WFSA, but the simplest involves using standard epsilon arcs to represent the back-off transitions.  This is not exact, in the sense that it is conceivable in some cases that a back-off weight could be lower than a non-back-off arc associated with the same sequence, but practically speaking this effect seems to have a negligible impact on ASR quality.  An exact epsilon representation has the further drawback of increasing the size of the grammar transducer.

Using the toy corpus foobar.corpus, described above, we will first train a 2-gram language model with mitlm, using modified Kneser-Ney smoothing.

```
$ estimate-ngram -o 2 -t foobar.corpus -wl foobar.2.arpa
```

Next, we will convert this to an equivalent WFST using the [arpa2fst.py](http://code.google.com/p/transducersaurus/source/browse/prototypes/arpa2fst.py) tool,
```
$ ./arpa2fst.py foobar.2.arpa foobar.g.fst.txt foobar
```

and compile this into a graph with the following command,
```
$ fstcompile --arc_type=log --acceptor=true --ssymbols=foobar.g.ssyms --keep_state_numbering --isymbols=foobar.word.syms foobar.g.fst.txt | \
     fstdraw --acceptor=true --ssymbols=foobar.g.ssyms --isymbols=foobar.g.isyms --portrait=true | \
     dot -Tpdf > foobar.g.pdf
```

which should in turn produce a graph similar to the one below.

<img src='http://i.imgur.com/N3YaR.jpg' width='850' />


Note that because the bigram 'foo foo' appeared in the training data there is a corresponding self-loop on state 'foo'.  There is no such example of 'bar bar' and thus accounting for novel occurrences of such a sequence would require passing through the back-off epsilon state.  Of course this behavior is not unique to the WFST representation, but it can in some cases be easier to follow than the raw ARPA model.

## Pronunciation lexicon **L** ##

The pronunciation lexicon WFST is a simple representation of the pronunciation dictionary where each entry is constructed as a single path - one arc for each input phoneme in the pronunciation and an output symbol corresponding to the word.

Using the pronunciation dictionary foobar.dic that we created earlier, along with the [lexicon2fst.py](http://code.google.com/p/transducersaurus/source/browse/prototypes/lexicon2fst.py) tool, the following command should produce an equivalent WFST representation,
```
$ ./lexicon2fst.py foobar.dic foobar > foobar.l.fst.txt
```

and this can once again be transformed into a graph with,
```
$ fstcompile --arc_type=log --isymbols=foobar.l.isyms --osymbols=foobar.l.osyms foobar.l.fst.txt | \
     fstdraw --isymbols=foobar.l.isyms --osymbols=foobar.l.osyms --portrait=true | \
     dot -Tpdf > foobar.l.pdf
```
<img src='http://i.imgur.com/bL6UM.png' width='700' />

In order to ensure that the lexicon can handle sequences of words, not just single words it is necessary to perform the **closure** of the lexicon prior to composing it the with the grammar.  This adds an epsilon arc from each final state to the initial state, allowing the input to loop through the vocabulary.

The end of each word is followed by an auxiliary symbol, e.g., #101.  These symbols serve to ensure that any occurrence of homophones, such as
```
foo     f uw
bar     f uw
```
in the example dictionary do not make the resulting WFST non-determinizable.  In this case, each homophone is accompanied by a different auxiliary symbol, thus guaranteeing that the result will be determinizable.

## Context dependency **C** ##
The **C** transducer will form the final component of our cascade. The context-dependency transducer encodes a mapping between monophones and triphones (or n-phones), that is, it contextualizes the monophone sequences.  These triphones are typically mapped directly to the physical triphones in the acoustic model, after accounting for any tied states that the acoustic model may have defined.

A simple example of a deterministic, inverted triphone model corresponding to a two phone phoneme inventory,

foobar.phons
```
f
b
```

can be constructed with the [cd2fst.py](http://code.google.com/p/transducersaurus/source/browse/prototypes/cd2fst.py) tool using the following command,
```
$ ./cd2fst.py phons aux foobar > foobar.c.fst.txt
```

this can be compiled into a graph then using the command,
```
$ fstcompile --arc_type=log --ssymbols=foobar.c.ssyms --isymbols=foobar.c.isyms --osymbols=foobar.c.osyms foobar.c.fst.txt | \
     fstdraw --portrait=true --isymbols=foobar.c.isyms --osymbols=foobar.c.osyms | \
     dot -Tpdf > foobar.c.pdf
```
which should produce something similar to the graph below (the command will not produce human-readable state symbols, this is slightly more compliated).
<img src='http://i.imgur.com/StATT.jpg' width='850' />

Note the auxiliary symbol loops #101, #102, etc.  These are required in order to peform composition with the lexicon above, but are deleted on the input side in order to maintain compatibility with the acoustic model. Alternatively the auxiliary arcs in the C and lower components can be simulated during composition, but we mark them explicitly for the sake of clarity.

## Going lower ##
In some cases it may be desirable to map down to HMM distributions, however, as each additional component tends to further increase the size of the cascade, and the benefits of further mapping down to the distribution level with WFSTs appear to be limited, in most cases we stop at the **C** level.  If one did want to map down to the HMM distribution level it would be necessary to mark the input sides of the auxiliary arcs with auxiliary symbols.

## Putting it all together ##

In order to actually perform recognition on novel utterances it is necessary to combine the component knowledge sources.  More advanced techniques make it possible to do this on-the-fly, but for the purposes of this tutorial it will suffice to outline a static composition process.

The integrated cascade construction process is achieved by iteratively combining the component knowledge sources in a right-to-left fashion, in this case starting with the **G** and **T** transducers and working leftwards to the **L** and **C** transducers while optionally performing optimizations along the way.  The full set of operations is described below,
```
C⚬(det(L⚬(G⚬T)))
```

where the ⚬ operator denotes composition and the 'det' operator denotes determinization.  In some cases minimization can significantly reduce the size of the graph, but in practice this still has limited impact on RTF and should not affect accuracy. There are many other, additional optimization operations but our findings have indicated that the only really essential operation is the determinization of the L⚬(G⚬T) sub cascade.  Given the amount of time, memory and space that most of the optimization algorithms require for large LVCSR inputs, in most cases it is probably not worth the trouble.

In our case it will suffice to simply build the cascade from scratch using the compilation [make-cascade-clgt.sh](http://code.google.com/p/transducersaurus/source/browse/prototypes/make-cascade-clgt.sh) tool, the models we downloaded ( [hmmdefs.gz](http://www.gavo.t.u-tokyo.ac.jp/~novakj/hmmdefs.gz),
[tiedlist.gz](http://www.gavo.t.u-tokyo.ac.jp/~novakj/tiedlist.gz)  )and the following command,
```
$ ./make-cascade-clgt.sh foobar.2.arpa foobar.dic foobar hmmdefs tiedlist 
```

which can be compiled into a graph with a little extra effort (the visual compilation of this graph requires some extra massaging so the command is not included).  The image below shows a subsection of the fully composed and optimized **CLGT** cascade.

<img src='http://i.imgur.com/GrHn6.png' width='800' />

Note that the input side of the integrated cascade is now triphone sequences, and this maps directly to word sequences on the output side.  The intermediate information has been folded into the graph during our repeated composition operations.  You can also see the silence class model at work, it is responsible for the loop between states **3** and **4**.

## Testing ##
If you have successfully managed to compile Juicer you can run a test on the resulting mini cascade with the following command,
```
$ juicer     -inputFormat htk     \
     -lmScaleFactor 13\
     -inputFName foobar.scp\
     -htkModelsFName hmmdefs\
     -mainBeam 230\
     -threading\
     -sentStartWord "<s>"\
     -sentEndWord "</s>"\
     -silMonophone "sil"\
     -lexFName foobar.dic\
     -pauseMonophone sp\
     -inSymsFName foobar.hmm.syms\
     -fsmFName foobar.clgt.fst.txt\
     -outSymsFName foobar.word.syms
```

assuming that foobar.scp contains list of .mfc files to decode:

foobar.scp
```
foobarfoofoobar.mfc
```

Note: Each .mfc file should correspond to a recording that you have made at a 16kHz sample rate (because our acoustic model has been trained on 16kHz speech data).  You can use the HTK program HCopy to convert the file, using a configuration file such as:
juicer-hcopy.conf
```
TARGETKIND = MFCC_0_D_A_Z
TARGETRATE = 100000.0
SAVECOMPRESSED = F
SAVEWITHCRC = F
WINDOWSIZE = 250000.0
USEHAMMING = T
PREEMCOEF = 0.97
NUMCHANS = 26
CEPLIFTER = 22
NUMCEPS = 12
SOURCEFORMAT = WAV
BYTEORDER = VAX
ENORMALISE = T
ZMEANSOURCE = T
USEPOWER = T
```
and the HCopy command,
```
$ HCopy -C juicer-hcopy.conf foobarfoofoobar.wav foobarfoofoobar.mfc
```

If you managed all of that, it should output something like,
```
iInputVecSize 39 GetArraySize 39
</s> foo <sil> <sil> <sil> foo <sil> <sil> <sil> bar <sil> <sil> foo <sil> foo <sil> <s> <sil>
```

basically a series of 'foo's and 'bar's.  Don't expect it to be very accurate though, the model is incredibly simple and not very sophisticated.  For something more robust try the other [README.txt](http://code.google.com/p/transducersaurus/source/browse/prototypes/README.txt) tutorial.

# Further reading #
That's it for the Transducersaurus WFST tutorial.  This tutorial has tried to cover the fundamentals of WFST cascade construction, but it has necessarily left out a large number of details.

If you are interested in finding out more about speech recognition with Weighted Finite-State Transducers, take a look at the following resources,

  * [Speech Recognition with Weighted Finite-State Transducers](http://www.cs.nyu.edu/~mohri/pub/hbka.pdf) (.pdf) by Mohri et. al. (the canonical reference)
  * [Introduction to the Use of Weighted Finite State Transducers (WFSTs) in Speech and Language Processing](http://www.furui.cs.titech.ac.jp/~dixonp/pubs/apsipa_09_tutorial_dixon_furui.pdf) (.pdf) by Paul R. Dixon (really good stuff)
  * [Applied Combinatorics on Words](http://www-igm.univ-mlv.fr/~berstel/Lothaire/AppliedCW/AppCWContents.html) by Lothaire (an excellent and **free** general resource on state machines)
  * [An Empirical Comparison of the T3, Juicer, HDecode and Sphinx3 Decoders](http://www.gavo.t.u-tokyo.ac.jp/~novakj/Interspeech_Novak.pdf) (.pdf) by Novak et. al. (shameless self-promotion)
  * [WFST-based Algorithms](http://www.gavo.t.u-tokyo.ac.jp/~novakj/wfst-algorithms.pdf) (.pdf) by Josef Novak (another shameless plug)

### Static On-The-Fly Composition ###
This tutorial focused on a standard cascade construction algorithm, the **C⚬det(L⚬G)** approach, however it may in fact be preferable to modify this to a **(C⚬det(L))⚬G** approach using static on-the-fly composition as described in <a href='http://research.google.com/pubs/archive/35539.pdf'>A Generalized Composition Algorithm for Weighted Finite-State Transducers</a>.  I've added a build script to the project for this purpose, [make-cascade-clg-otf.sh](http://code.google.com/p/transducersaurus/source/browse/prototypes/make-cascade-clg-otf.sh), and written up a short series of experiments investigating the merits of this approach over at http://probablekettle.wordpress.com/2011/02/25/static-on-the-fly-composition-for-integrated-asr-cascades/ .

That's it!  If you have questions, problems or bug reports please feel free to let me know.  I'm sure there are still issues with the distribution - I ran into several myself while writing this tutorial.