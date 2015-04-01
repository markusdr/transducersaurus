### Transducersaurus quick-start guide ###

This guide is intended to help new users get started with the Transducersaurus toolkit.  It provides a step-by-step recipe for generating a working Automatic Speech Recognition (ASR) cascade based on the Weighted Finite-State Transducer (WFST) paradigm, which is suitable for simple Large Vocabulary Continuous Speech Recognition (LVCSR) tasks.  The guide intentionally focuses on small models in order to ensure that the resulting WFST cascades can be integrated and optimized in a reasonable amount of time, even on commodity hardware.

**Intended audience**

The guide is intended for motivated undergraduate or early graduate students who are interested in WFST-based ASR or just ASR in general.  A basic knowledge of the command line, linux/unix standard tools and how to compile source code is taken for granted.  No prior knowledge of the WFST paradigm is expected or required, but it may provide some further insight.

**Topics not covered**

This guide is not intended to provide any in-depth background on WFST-based ASR.  Users who are interested in finding out more should refer to the original CascadeTutorial for the initial release. In particular the list of additional theoretical references at the bottom of the tutorial should serve as a good starting point.

### System requirements ###
The Transducersaurus toolkit itself is Python based and is thus largely OS-independent.  Users have successfully reported using it on various Linux distributions, OSX and Windows 7.  I have personally used it successfully under Ubuntu (Intrepid), CentOS, and OSX.  This tutorial was compiled and tested on a MacBook Pro 6,2 running OSX 10.6.7 equipped with a dual core Intel Core i7 processor running at 2.8GHz with 8GB of main system memory.  A machine with 4GB of memory should be sufficient to run all the examples below, and 2GB should be sufficient for the simplest examples.  GCC 4.4 and other standard linux tools were installed using [MacPorts](http://www.macports.org/).

### Dependencies ###
In addition to the Transducersaurus distribution itself there are two dependencies that you will need to install in order to build and successfully test a working WFST-based ASR cascade.  These are,

  * [OpenFst](http://www.openfst.org) The toolkit relies on OpenFst for all low-level composition and optimization routines.  Compilation should be straightforward, but it is essential that the following configure command is used, in order to ensure that transduceraurus has access to the alternative composition algorithm.  See [edobashira](http://www.edobashira.com/2010/08/openfst-12.html) or the OpenFst website for further details:
    * `$ ./configure --enable-compact-fsts --enable-const-fsts --enable-far --enable-lookahead-fsts --enable-pdt`
  * [Juicer](http://juicer.amiproject.org/juicer) Juicer is an open source WFST decoder maintained by IDIAP.  It is not required to build models, but will be used to perform ASR.  The toolkit actually supports several different decoders but at present Juicer is the only one available under an OSS license.  Finally, compiling Juicer can be challenging and is beyond the scope of this tutorial, but there is an excellent build tutorial at:
    * http://nsh.nexiwave.com/2010/05/speech-decoding-engines-part-1-juicer.html
    * Alternatively, for OSX users I have created a bundle which includes Juicer as well as the required dependencies - aside from HTK, and a special build script:  http://www.gavo.t.u-tokyo.ac.jp/~novakj/juicer-osx.tgz
  * [Mercurial](http://mercurial.selenic.com/) is the revision control system utilized by the toolkit on googlecode.  Download and install it in order to check out the latest version of the source code.  At some point a tarball will be made available, but we aren't quite there yet.

### Getting started ###
The remainder of this guide is a simple recipe for setting up Transducersaurus and building a working cascade from the open source acoustic and language models that are provided below. It assumes that the OpenFst binaries as well as the juicer WFST decoder are accessible from the $PATH variable, and that the mercurial DRCS is installed.

**The recipe**

First setup a sandbox and checkout the toolkit,
```
$ mkdir tutorial
$ cd tutorial
$ hg clone https://code.google.com/p/transducersaurus/ 
$ cd transducersaurus
$ ./mk-sandbox.sh ../distro
$ cd ../distro
```
this will setup a local copy of the python tools in the 'distro' folder.

Next we need three basic language resources in order to build our cascade. These include an acoustic model, a pronunciation dictionary and a language model. For the sake of simplicity I have packaged some suitable English language models for the tutorial and made them available from the link below. These models are derived from [Keith Vertanen's](http://www.keithv.com/software/) excellent open source models. I have heavily pruned the language model in order to ensure that this tutorial builds quickly and efficiently on even low-spec machines, but we will utilize a 64k vocabulary and a 3-gram LM, so the result will still serve as an interesting LVCSR example. In practice we would prefer to utilize the full-size trigram model, but in previous experiments this required up to 13GB and required 20~40 minutes for the simplest builds, making it unreasonable for this guide.

The specs for the models are as follows,

  * Acoustic model: 8000 tied states, 32 gaussians, trained on the WSJ corpus
  * Lexicon: 64k vocabulary
  * Language model: 64k vocabulary, 3-gram, pruned to 522530 bigrams, 173445 trigrams

Download these models to your 'distro' directory,
```
$ wget http://www.gavo.t.u-tokyo.ac.jp/~novakj/tutorial-data.tgz
$ tar -xzvf tutorial-data.tgz
```
This will unpack the LM - **tutorial-lm.arpa**, the lexicon - **tutorial-lexicon.dic**, the HTK format acoustic model - **tutorial-am/**, and the set of two test utterances, **jtune/**. Now that we have all of the resources available the remainder of the cascade construction and optimization process can be achieved with a single command. For our first build we will utilize the lookahead composition approach as this is the simplest, fastest and most memory efficient build:
```
$ ./transducersaurus.py \
         --amtype htk \
         --tiedlist tutorial-am/tiedlist \
         --hmmdefs tutorial-am/hmmdefs \
         --lexicon tutorial-lexicon.dic \
         --grammar tutorial-lm.arpa \
         --command "(C*det(L)).G" \
         --convert j \
         --basedir auto \
         --prefix test \
         --verbose
```
The above command breaks down as follows,

  * '--amtype htk' indicates that we will be using HTK format acoustic models
  * '--tiedlist tutorial-am/tiedlist' indicates the location of the HTK format tiedlist
  * '--hmmdefs tutorial-am/hmmdefs' indicates the location of the HTK format hmmdefs files
  * '--lexicon tutorial-lexicon.dic' indicates the location of the pronunciation lexicon
  * '--grammar tutorial-lm.arpa' indicates the location of the ARPA format language model
  * '--command "(C\*det(L)).G" indicates the actual build algorithm to use in cascade construction. In this case we will use a simple three model combination, C, L, G with lookahead composition and a bare minimum of optimization.
  * '--convert j' indicates that the final cascade should be converted to a format suitable for use inside of the Juicer decoder

> The remaining parameters indicate the desired file naming conventions and how much information to display during construction.  The supported '--command' syntax is fairly rich and described in detail on the CascadeCompilationGrammar wiki.

The above command should produce a detailed step-by-step description of what it is doing, and will output the specific OpenFst commands being called.  The build process should also be quite fast; on my MacBook Pro the above command completed in approximately 1m14s, but this will no doubt vary based on your machine specs.

At this point we are ready to start decoding.  The last two lines of the command output specify the final ASR cascade and the associated wordlist,
```
test-aCcdetaLbboG/test.cdetlg.lkhd.fst.txt
test-aCcdetaLbboG/test.word.syms
```
which we will use to run the decoder,
```
$ ./juicer-test.sh \
        test-aCcdetaLbboG/test.cdetlg.lkhd.fst.txt \
        tutorial-lexicon.dic \
        test-aCcdetaLbboG/test.word.syms \
        test-aCcdetaLbboG/test.hmm.syms \
        tutorial-am/hmmdefs 

iInputVecSize 39 FrameSize 39
<s> gasoline pump prices plunged an average of nearly nine cents a gallon over the last week </s> 
<s> the decline in the average price of self service regular unleaded tipped the is the biggest decline 
since the iraqi invasion of kuwait august second </s>
```

These results are reasonable, but if we check the associated reference transcription for the first utterance, located in **jtune/tune-ju-htk.trn**,
```
<s> gasoline pump prices plunged an average of nearly nine cents a gallon over the last week 
and could drop a bit more because of weakening demand and excess supplies </s> (4o6c0i01) 
```
it should be clear that nearly half the utterance has been ignored during decoding.  The reason for this is that the utterance contains a lengthy pause, and our basic models have no means of accounting for silences.  One solution to this is to utilize a silence class WFST, and this can be accomplished by simply modifying the previous '--command' to include the silence class transducer.
```
$ ./transducersaurus.py \
         --amtype htk \
         --tiedlist tutorial-am/tiedlist \
         --hmmdefs tutorial-am/hmmdefs \
         --lexicon tutorial-lexicon.dic \
         --grammar tutorial-lm.arpa \
         --command "(C*det(L)).(G*T)" \
         --convert j \
         --basedir auto \
         --prefix test \
         --verbose
```
This will produce a larger final cascade (187MB vs. 99MB in binary format), but one that supports arbitrary silences.  As before, the final model and associated word list will be output at the end of the build process.  Using the new models we can run the test again,
```
./juicer-test.sh \
        test-aCcdetaLbboaGcTb/test.cdetlgt.lkhd.fst.txt \
        tutorial-lexicon.dic \
        test-aCcdetaLbboaGcTb/test.word.syms \
        test-aCcdetaLbboaGcTb/test.hmm.syms \
        tutorial-am/hmmdefs 

iInputVecSize 39 FrameSize 39
<s> gasoline pump prices plunged an average of nearly nine cents a gallon <sil> over the last week <sil>
 in could drop the bid more because of weakening demand in excess supplies </s> 
<s> the decline in the <sil> average price of self service regular unleaded <sil> is the biggest decline
 since the iraqi invasion of kuwait <sil> august second </s>
```
Although it is still not perfect, the new ASR hypothesis is significant improvement over the original, and the decoder is no longer being foiled by silences.  In order to further improve the results it would probably be necessary to user a larger or more judiciously pruned LM.

Thus far we have looked at two different build processes, but have not yet touched on optimization procedures.  Depending on the build algorithm it is often desirable to optimize the recognition cascade by applying optimization algorithms such as **determinization**, **minimization**, and/or **weight-pushing**.  The first algorithm serves to remove ambiguity from the recognition network, the second removes redundancies, and the third attempts to aggregate arc weights either at the beginning or the end of the network.  For more detailed descriptions and references pertaining to these algorithms, see the CascadeTutorial and included references.

For our purposes it is sufficient to note that these optimization algorithms serve to speed up the decoding process by eliminating ambiguity, shrinking the ASR network and pushing weights to the front of the graph.  In practice however, these optimizations come at a cost.  This cost shows up in terms of increases computation time, increased memory requirements, and paradoxically often increased storage space requirements.

For the sake of completeness we will also look at a build utilizing the standard composition algorithm (as opposed to lookahead composition which was used in the previous builds).
```
/transducersaurus.py \
          --amtype htk \
          --tiedlist tutorial-am/tiedlist \
          --hmmdefs tutorial-am/hmmdefs \
          --lexicon tutorial-lexicon.dic \
          --grammar tutorial-lm.arpa \
          --command "C*det(L*G)" \
          --convert j \
          --basedir auto \
          --prefix test \
          --verbose
```
The above command should produce a cascade equivalent (but not exactly the same) to the first in terms of size, and which should produce the same ASR results as the first build command.  Nevertheless it will require a much larger amount of memory (1.3GB on my MacBook), and considerably longer to compile the cascade.  The majority of the build time will be spent on the 'det(LG)' operation, and on my machine the full build with this command required approximately 9m17s to complete.  We can further optimize the cascade by applying minimization as well,
```
/transducersaurus.py \
          --amtype htk \
          --tiedlist tutorial-am/tiedlist \
          --hmmdefs tutorial-am/hmmdefs \
          --lexicon tutorial-lexicon.dic \
          --grammar tutorial-lm.arpa \
          --command "C*min(det(L*G))" \
          --convert j \
          --basedir auto \
          --prefix test \
          --verbose
```
which will require roughly the same amount of memory, and an additional couple of minutes to complete.  In this case the final cascade will be reduced from 116MB to 48MB - a considerable savings.  Nevertheless it is important to note that the savings from these optimizations tend vary considerably based on the structure of the input models.  In our case we have a large (64k) vocabulary with many alternative pronunciations, and a very sparse language model.  This is partially responsible for the large benefit from minimization in this case.  A larger, denser LM would likely result in less of a savings.  The other concern we have is the RealTime Factor (RTF), or decoding speed.  It may be interesting to evaluate the impact that different optimization procedures have on the RTF vs the word accuracy that the decoder is able to achieve for a specific beam value.

In practice I have found that utilizing the '(C\*det(L)).(G\*T)' build, but performing the CL.GT composition on-the-fly during decoding provides a very favorable balance between RTF vs. WACC, final model size (just CL(12MB)+GT(40MB)=52MB vs. 116MB in this example) and build time (~1m for Cdet(L) GT vs. ~15m for Cmin(det(L\*G))).  Unfortunately no OSS implementation currently exists, but this will be remedied in the immediate future.  Finally, In practice some of the standard build specs can be improved by manipulating the LM prior to compilation, but this at the cost of added complexity.

That's it, go forth and experiment!