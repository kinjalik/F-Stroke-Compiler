( func test ( ) (
    ( setq x 0 )
    ( while ( nonequal x 10 ) (
        ( cond ( equal x 5 )
            ( break )
            ( setq x ( plus x 1 ) )
        )
      )
    )
    ( return x )
  )
)
( func test2 ( ) (
    ( setq x 0 )
    ( while ( nonequal x 10 ) (
        ( cond ( equal x 5 )
            ( break )
            ( setq x ( plus x 1 ) )
        )
      )
    )
    ( return x )
  )
)

( prog (
    ( setq x ( test ) )
    ( return ( test2 ) )
) )