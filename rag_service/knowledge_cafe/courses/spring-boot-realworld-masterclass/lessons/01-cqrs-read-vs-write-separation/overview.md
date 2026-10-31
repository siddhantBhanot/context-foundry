# CQRS Read vs Write Separation

In `spring-boot-realworld`, command mutations flow through `ArticleCommandService` and `ArticleRepository`, whereas read queries use `ArticleQueryService` and `ArticleReadService` returning `ArticleData` DTOs directly from MyBatis.