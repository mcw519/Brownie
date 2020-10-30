import pynini

def list2fst(x, in_syms, out_syms):
    """
        Input:
            x is like:
                [['0', '1', '世界', '世博會', '0.1053605157'], ['1', '0', '博覽會', '<eps>'],
                ['0', '2', '一個', '一個巨星的誕生', '0.1053605157'], ['2', '3', '巨星', '<eps>'],
                ['3', '4', '的', '<eps>'], ['4', '0', '誕生', '<eps>']]
            in_syms, out_syms is symbols table (dict)
        Return:
            Fst
    """
    if x is not None:
        fst = pynini.Fst()
        fst.add_state()
        fst.set_start(0)
        for i in x:
            if len(i) == 5:
                state_in, state_out, arc_in, arc_out, arc_weight = i
                state_in = int(state_in)
                state_out = int(state_out)
                arc_in = int(in_syms[arc_in])
                arc_out = int(out_syms[arc_out])
                arc_weight = pynini.Weight("tropical", float(arc_weight))
                fst.add_state()
                fst.add_arc(state_in, pynini.Arc(arc_in, arc_out, arc_weight, state_out))
            
            elif len(i) == 4:
                state_in, state_out, arc_in, arc_out = i
                state_in = int(state_in)
                state_out = int(state_out)
                arc_in = int(in_syms[arc_in])
                arc_out = int(out_syms[arc_out])
                arc_weight = pynini.Weight("tropical", 0)
                fst.add_state()
                fst.add_arc(state_in, pynini.Arc(arc_in, arc_out, arc_weight, state_out))
            
            else:
                fst.set_final(0)
        
        return fst.optimize()
    
    else:

        raise(ValueError, "empty fst list")