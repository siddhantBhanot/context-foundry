# Stateless JWT Authentication Filter Chain

`JwtTokenFilter` extracts the `Token <jwt>` header, validates the signature via `DefaultJwtService`, and populates Spring SecurityContext.