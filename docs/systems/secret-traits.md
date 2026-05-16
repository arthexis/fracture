# Secret Traits

Characters can have server-side secret traits stored on the character Attribute
`secret_traits`. These traits are not intended for ordinary player inspection.

## True Sight

`True Sight` lets a character see account deck information in character display
names. When a character with True Sight sees a player character, the target's
name is rendered with the target account deck's top and bottom cards:

```text
Name [TOP/BOTTOM]
```

The top card is the next card that would be drawn from the account-linked deck.
The bottom card is the first card in the deck list. Seeing these cards does not
draw or reshuffle the deck.

Standard cards use Arthexis suit codes:

- Daggers: `D`
- Spindles: `S`
- Vessels: `V`
- Masques: `M`

Examples: `AD`, `10M`, `QV`, and `7S`.

Jokers render as:

- `JokerA`: `XX`
- `JokerB`: `XY`
- `JokerC`: `YY`

The `arthexis` character receives `True Sight` by default.
