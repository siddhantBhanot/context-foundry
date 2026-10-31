---
id: spring-boot-realworld-masterclass
title: Spring Boot RealWorld: CQRS, JWT Auth & GraphQL Architecture
description: Interactive onboarding guide covering the CQRS read/write separation, MyBatis mappers, JWT token filter chain, and Netflix DGS GraphQL resolvers in spring-boot-realworld.
target_service: spring-boot-realworld
difficulty: Intermediate
estimated_duration: 30 mins
domain: Engineering & Microservices
group: technical
tags:
  - spring-boot-realworld
  - team-tutorial
---

# Spring Boot RealWorld: CQRS, JWT Auth & GraphQL Architecture

Interactive onboarding guide covering the CQRS read/write separation, MyBatis mappers, JWT token filter chain, and Netflix DGS GraphQL resolvers in spring-boot-realworld.

## 1. CQRS Read vs Write Separation

- **Summary**: How ArticleQueryService and MyBatis ReadServices separate read projections from domain command repositories.
- **Context**:
  - `lessons/01-cqrs-read-vs-write-separation/overview.md`

- **Knowledge Check**:

  - **Question**: Which service handles read-only article queries and pagination in spring-boot-realworld?
  - **Type**: multiple_choice
  - **Options**:
    - [ ] ArticleCommandService
    - [x] ArticleQueryService
    - [ ] MyBatisArticleRepository
    - [ ] TagsApi
  - **Explanation**: ArticleQueryService executes read-side queries using ArticleReadService and enriches DTOs with favorites and following status.


## 2. Stateless JWT Authentication Filter Chain

- **Summary**: Tracing requests through WebSecurityConfig, JwtTokenFilter, and DefaultJwtService.
- **Context**:
  - `lessons/02-stateless-jwt-authentication-filter-chain/overview.md`

- **Knowledge Check**:

  - **Question**: What HTTP Authorization header prefix does JwtTokenFilter expect?
  - **Type**: multiple_choice
  - **Options**:
    - [ ] Bearer
    - [x] Token
    - [ ] Basic
    - [ ] ApiKey
  - **Explanation**: RealWorld Conduit specification uses `Authorization: Token <jwt>`.

