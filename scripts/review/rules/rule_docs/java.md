#### Obvious Typos or Spelling Errors
- Spelling errors in variable names, method names, or class names at their declaration sites (confirm by searching for naming conventions of similar identifiers using `code_search`)
- Strings in log messages or exception messages containing spelling errors that affect readability
- Do not report spelling errors at reference sites, as these are typically determined by the declaration

#### Dead Code
- Code blocks that can never be reached (e.g., branches where the condition is always false, code after a return statement)
- Variables that are declared but never read or referenced
- Large blocks of commented-out code (with no apparent intent to preserve)

#### Logic Error Detection
- Incorrect if-condition logic (use `file_read` to examine surrounding context and confirm expected logic)
- Boundary condition handling errors (pay special attention to index and array length checks)
- Misuse of boolean logic operators (precedence and short-circuit evaluation issues)
- Obvious infinite loops or recursion without termination conditions
- Use of return/break/continue where exiting is not intended
- Missing break statements in switch cases causing unintended fall-through
- Intentional fall-through lacking explanatory comments
- Code patterns that may cause NPE (confirm risk by inspecting the data source call chain using `file_read` and `code_search`)
- Missing parentheses in logical expressions that may cause execution order to differ from intent

#### Severe Performance Issues
- Database queries executed inside loops (use `code_search` to confirm whether the method call involves database operations)
- N+1 query problems (suggest batch query optimizations)
- Processing large datasets without pagination (use `file_read` to understand data scale and processing context)
- Inefficient algorithm implementations in nested loops (O(n^2) or higher complexity where a more optimal solution exists)

#### Thread Safety Issue Detection
Only flag thread safety issues in the following cases:
- **Race conditions**: A "check-then-act" pattern exists where intermediate state may be altered by another thread
- **Non-atomic compound operations**: Multi-step operations that require atomicity but lack synchronization mechanisms
- **Unsafe lazy initialization**: Double-checked locking defects in singleton patterns or cache implementations
- **Concurrent writes to thread-unsafe collections**: Modifications to non-thread-safe collections such as ArrayList or HashMap in a multi-threaded environment

Do not report in the following cases:
- **Local variables within methods**: These are inherently thread-safe, as each thread has its own copy
- **Single-threaded context usage**: No evidence of multi-threaded invocation (confirm by searching for relevant call contexts using `code_search`)
- **Read-only operations**: Even with non-thread-safe data structures, if only read operations are performed
- **Immutable objects**: References to final fields pointing to immutable objects
- **Proper synchronization already in place**: Code already uses synchronized, Lock, atomic classes, or other correct synchronization mechanisms
- **Components designed for single-threaded use**: Such as the building phase of a Builder pattern, temporary data transfer objects, etc.

#### Google Java Style, Effective Java (3rd Ed.) & Modern Java 17/21 Idioms
Respect repository-local `checkstyle.xml`, `pmd.xml`, Spotless, and `.editorconfig` rules first when present; otherwise apply these authoritative conventions (treat correctness/contract hazards as P1 blocking and purely stylistic items as P2 advisory):
- **`@Override` & Object Contracts (*Effective Java* Items 10–14, 40)**: Require `@Override` on every overridden superclass/interface method; overriding `equals` without `hashCode` (or violating symmetry/transitivity, or mutating keys stored in `HashMap`/`HashSet`) is a P1 bug.
- **Null Safety & `Optional` Discipline (*Effective Java* Item 55, Google Java Style)**: Validate non-null parameters at public boundaries (`Objects.requireNonNull`); return empty collections/arrays instead of `null` (*Item 54*); use `Optional<T>` strictly as a return type—never for fields, method parameters, or collections—and never call `Optional.get()` without proving presence (`orElseThrow`, `map`, `ifPresent`).
- **`try-with-resources` & Resource Safety (*Effective Java* Item 9)**: Always close `AutoCloseable` streams, JDBC connections/statements/result sets, HTTP responses, and `Files.walk`/`Files.lines` streams with `try-with-resources` rather than manual `finally` blocks.
- **Numeric, Currency & String Pitfalls (*Effective Java* Items 60–61)**: Never use `float`/`double` or `new BigDecimal(double)` for monetary/exact decimal calculations—use `BigDecimal.valueOf(...)` or `new BigDecimal(String)`; guard boxed primitive unboxing (`Integer`/`Long`/`Boolean`) against `NullPointerException`; specify `StandardCharsets.UTF_8` / `Locale.ROOT` explicitly on byte conversions and case folding.
- **Streams, Immutability & Modern Java 17/21 (*Effective Java* Items 17, 45–48)**: Keep Stream pipeline lambdas pure and side-effect-free (do not mutate external `ArrayList`/`HashMap` inside `forEach`/`map`); prefer `List.of`/`Map.of`/`Set.of`, `record` value carriers, `sealed` hierarchies, and exhaustive pattern-matching `switch` expressions where supported by the project's Java target.
- **Structured / Parameterized Logging (SLF4J)**: Use parameterized placeholders (`log.info("Processed item {}", id)`) rather than string concatenation, pass `Throwable` as the final argument (`log.error("Failed for {}", id, ex)`), and never log secrets, tokens, or credentials.

#### Java / Spring Boot Test Hygiene & Annotation Discipline
When reviewing `*Test.java`, `*UnitTest.java`, `*IntegrationTest.java`, or `*ContractTest.java` files in Java / Spring Boot microservices, strictly enforce the following 5 rules (flag violations as P1 blocking issues):
1. **Single Test-Group Annotation per Test Class**:
   - A test class must declare **at most one** test-group annotation: `@UnitTest`, `@IntegrationTest`, or `@ContractTest`.
   - Never combine 2 test-group annotations in any combination (e.g., `@UnitTest` + `@IntegrationTest` or `@IntegrationTest` + `@ContractTest`), as this causes the test class to execute twice in CI pipelines.
2. **Strict `@ContractTest` Scope**:
   - `@ContractTest` is reserved exclusively for contract tests that verify interaction between **2 or more services**.
   - Never annotate single-service unit, controller, or repository integration tests with `@ContractTest`.
3. **Explicit Testcontainer Startup in `@IntegrationTest`**:
   - Use `@IntegrationTest` only when verifying real database/cache interaction or when logic cannot be covered by unit tests.
   - Every `@IntegrationTest` class that interacts with databases/caches must explicitly start its required Testcontainers in `@BeforeAll` (e.g., `PostgresTestContainer.runContainer()`, `RedisTestContainer.runContainer()`, `MongoTestContainer.runContainer()`). Never rely on containers implicitly left running by a previous test class, and never commit `@Disabled("...requires testcontainers")` on an `@IntegrationTest`.
4. **No Repository or Internal DB-Service Mocking in `@IntegrationTest`**:
   - In `@IntegrationTest`, never use `mock()`, `@Mock`, `@MockBean`, or `@MockitoBean` for database repositories (`*Repository`) or internal DB-backed domain services under test — `@IntegrationTest` must verify real DB interaction.
   - If repositories are mocked, the test is a unit test and must use `@UnitTest` without booting a full Spring/DB context.
   - In `@IntegrationTest`, mocks are restricted strictly to external boundaries not needed for testing the service logic (Feign clients, external HTTP calls, Pulsar clients/producers/consumers, external config/initializers).
5. **Centralized `application-test.yaml` with `@ActiveProfiles("test")`**:
   - Do not repeat common infrastructure-disabling properties (such as `"spring.cloud.consul.enabled=false"`, `"spring.cloud.discovery.enabled=false"`, `"vedge.otel.sdk.disabled=true"`) inline inside `@SpringBootTest(properties = {...})` across individual test classes.
   - Define shared test properties once in `src/test/resources/application-test.yaml` (or `application-test.properties`) and annotate the test class with `@ActiveProfiles("test")`.
