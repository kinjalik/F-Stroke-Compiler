( prog (
    ( setq v ( read 0 ) )
    ( setq b ( read 1 ) )
    ( setq l ( read 2 ) )
    ( setq res 0 )
    ( while ( equal 1 1 ) (
    	( cond
            ( equal ( minus v ( times ( divide v b ) b ) ) l )
            ( setq res ( plus res 1 ) )
        )
        ( setq v ( divide v b ) )
        ( cond ( equal v 0 ) ( return res ) )
      )
    )
  )
)