#!/usr/bin/python
import re

def make_hmmsyms( hmmdefs, eps, prefix, aux ):
    hmm_fp = open(hmmdefs,"r")
    hmm_ofp = open("PREFIX.hmm.syms".replace("PREFIX",prefix),"w")
    hmm_ofp.write("EPS 0\n".replace("EPS",eps))
    cnt = 0
    for line in hmm_fp:
        if not line.startswith("~h"):
            continue
        cnt +=1
        line = line.strip()
        line = re.sub(r"^~h \"","",line)
        line = re.sub(r"\"$", "", line)
        hmm_ofp.write("%s %d\n"%(line, cnt))
    hmm_fp.close()
    for a in aux:
        cnt += 1
        hmm_ofp.write("%s %d\n" % (a, cnt))
    hmm_ofp.close()
    return

def check_arpa_vocab( arpalm, lexicon, vocabfile, lastid ):
    """
       Read the unigram entries from an ARPA
       LM and check them against a pronunciation lexicon.
       Make sure there is at least one entry in the 
       lexicon for each unigram.
    """

    arpalm_fp = open(arpalm,"r")
    unigram = False
    missing = False
    vocab_afp = open(vocabfile,"a")
    for line in arpalm_fp:
        line = line.strip()
        if line=="": continue
        if line.startswith("\\1-grams"):
            unigram=True
            continue
        if line.startswith("\\2-grams") or line.startswith("\\end"):
            unigram=False
            break
        if unigram:
            parts = re.split(r"\s+",line)
            #Skip unk for now.
            if parts[1] not in lexicon:
                missing = True
                print "WARNING: Word \"%s\" from LM file %s does not have a corresponding entry in the pronunciation dictionary!"%(parts[1],arpalm)
                print "Adding \"%s\" to %s symbols list." %(parts[1],vocabfile)
                vocab_afp.write("%s\t%d\n"%(parts[1],lastid))
                lastid += 1
    vocab_afp.close()
    arpalm_fp.close()
    return missing

def load_vocab_from_lexicon( lexicon, prefix="test", eps="<eps>", failure=None ):
    """Load vocabulary from a pronunciation lexicon."""
    lexicon_fp = open(lexicon,"r")
    vocabfile = "%s.word.syms"%prefix
    word_ofp   = open(vocabfile, "w")
    vocab = {}
    count = 1
    word_ofp.write("%s 0\n"%eps)
    for line in lexicon_fp:
        line = line.strip()
        pron = re.split(r"\s+",line)
        word = pron.pop(0)
        if not word in vocab:
            word_ofp.write("%s\t%d\n"%(word,count))
            count += 1
        vocab[word]=pron
    if failure:
        word_ofp.write("%s\t%d\n" % (failure,count))
        count += 1
    lexicon_fp.close()
    word_ofp.close()
    return vocab, vocabfile, count

if __name__=="__main__":
    import sys

    vocab, vocabfile, lastid = load_vocab_from_lexicon( sys.argv[1], prefix=sys.argv[3], eps="<eps>" )

    missing = check_arpa_vocab( sys.argv[2], vocab, vocabfile, lastid )
    print "Missing LM words were added to %s:"%vocabfile,missing
