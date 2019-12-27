( func sum ( x ) (
    ( cond ( equal x 0 )
      ( return 0 )
      ( return ( plus x ( sum ( minus x 1 ) ) ) )
    )
  )
)

( prog ( ( return ( sum 10 ) ) ) )