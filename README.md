# Browine
Browine is a post-processing project for FST-based Automatic Speech Recognition.

## Goal
In this project the goal is increasing the recognition accuracy for ASR result more closer to user's application on specific domain name entity.  

## How would you generate personal grammar?
### Define custom vocabularies
If you have been used [Amazon Transcribe](https://docs.aws.amazon.com/transcribe/latest/dg/how-vocabulary.html) you must be familier this setting.  

Noted the first line (Phrase, SoundsLike, IPA, DisplayAs) and phrase column must be given and seperate each column by comma.  
Custom vocabularies table format is:
```
Phrase,SoundsLike,IPA,DisplayAs
世界博覽會,shi4-jie4-bo4-lan3-hui4,,世博會
一個巨星的誕生,,,一個巨星的誕生
EMMA ROSE,,EH1 M AH0 R OW1 Z,emmarose,
```

And variables definition is:
```
Phrase: Hypothesis string could be a sequence of error pattern or a word
SoundsLike: Mandarin phrase spelled by Mandarin syllables. Later will handle English phrase
IPA: IPA phoneme representation
DisplayAs:  Defines how the word or phrase looks
```

### Define user grammar
Grammar could point out where the entity appear to avoid unnecessary replace.  
One sample is how to enhance voice assistants accuracy to make a phone call situation. In this case anchor word is "CALL" and defined NE would appear between anchor and sentence end.
User grammar format is :
```
<SIGMA_STAR> CALL <CONTACT> <SIGMA_STAR> </CONTACT> </s>
```

And variables definition is:
```
<SIGMA_STAR>:   Special tag for filier words
<> and </>:    User specific tag pair
<s>:    Special tag for sentence start
</s>:   Special tag for sentence end
```

## Installation requirements
This project used the [OpenFst](http://www.openfst.org/twiki/bin/view/FST/WebHome) and [Pynini](http://www.openfst.org/twiki/bin/view/GRM/Pynini) toolkit.

### OpenFst
```
wget http://www.openfst.org/twiki/pub/FST/FstDownload/openfst-1.7.9.tar.gz
tar zxvf openfst-1.7.9.tar.gz && cd openfst-1.7.9
sudo ./configure --enable-grm
sudo make
sudo make install
```

### Pynini

```
conda install -c conda-forge pynini=2.1.0
```