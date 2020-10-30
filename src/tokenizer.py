# Copyright 2020 (author: Meng Wu)

import jieba
import jieba.posseg as pseg
#import hanlp


class HanlpTokenizer():

    def __init__(self, wsmodel="LARGE_ALBERT_BASE", posmodel="hanlp.pretrained.pos.CTB5_POS_RNN_FASTTEXT_ZH"):
        self.tokenizer = hanlp.load(wsmodel)
        self.tagger = hanlp.load(posmodel)

    def segment(self, x, mode="segment"):
        '''
            Input:
                x (string)
            Return:
                segment (string)
                segment_pos (string)
                seperate (list)
            Options:
                mode: segment/segment_pos/seperate
        '''
        hanlp_wd = self.tokenizer(x)

        if mode != "segment":
            pos_tag = self.tagger(hanlp_wd)
            
            if mode == "segment_pos":
                result = []
                for i, j in zip(hanlp_wd, pos_tag):
                    result.append("{}({})".format(i, j))

                return " ".join(result)
            
            else:
                
                return list(zip(hanlp_wd, pos_tag))
        
        else:

            return " ".join(hanlp_wd)


class JiebaTokenizer():
    def __init__(self, dict_file=None, cut_all=False, hmm=False):
        self.cut_all = cut_all
        self.hmm = hmm
        
        if dict_file is not None:
            jieba.set_dictionary(dict_file)

        self.ws_pos = pseg.POSTokenizer(jieba.dt)

    def reload_dict(self, dict_file):
        jieba.set_dictionary(dict_file)
        self.ws_pos = pseg.POSTokenizer()

    def segment(self, x, mode="segment"):
        '''
            Input:
                x (string)
            Return:
                segment (string)
                segment_pos (string)
                seperate (list)
            Options:
                mode: segment/segment_pos/seperate
        '''
        if mode != "segment":
            seg_result = self.ws_pos.cut(x, HMM=self.hmm)
            
            if mode == "segment_pos":
                result = []
                for i, j in seg_result:
                    result.append("{}({})".format(i, j))

                return " ".join(result)

            else:
                result = []
                for i, j in seg_result:
                    result.append((i, j))

                return result
        
        else:
            seg_result = jieba.lcut(x)

            return " ".join(seg_result)


class Tokenizer():
    '''
        Jieba/HanLP segmentor high level interface
    '''
    def __init__(self, backend="jieba", jieba_dict=None):
        self.backend = backend

        if backend == "jieba":
            from tokenizer import JiebaTokenizer
            
            if jieba_dict is not None:
                self.segmenter = JiebaTokenizer(jieba_dict)
            else:
                self.segmenter = JiebaTokenizer()
        
        elif backend == "hanlp":
            from tokenizer import HanlpTokenizer
            self.segmenter = HanlpTokenizer()
    
    def segment(self, x, mode="segment"):
        '''
            Input:
                x (string)
            Return:
                segment (string)
                segment_pos (string)
                seperate (list)
            Options:
                mode: segment/segment_pos/seperate
        '''
        segmenter = self.segmenter

        return segmenter.segment(x, mode=mode)