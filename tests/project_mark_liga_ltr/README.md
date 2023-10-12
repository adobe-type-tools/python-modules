# Liga LTR

This is a test project for mark-to-ligature attachment in left-to-right context.  
The `f_i` (`f_i_i`, `f_i_i_i`, etc.) ligatures within the UFO file are created using a [Python script](collateral/make_ligatures_ltr.py). They contain up to 9 anchor attachment points per role (above, below, etc.), which is the maximum supported by the FDK’s mark feature writer.  

The mark feature within this projects exercises ligature marks, as well as trimming anchor names for upper- and lowercase distinction – plus a random anchor to be skipped.  

	markfeaturewriter -t liga_ltr.ufo

