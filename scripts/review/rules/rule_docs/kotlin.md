#### Kotlin & Android Review Principles
> Favor precision over recall: report only real correctness, concurrency, lifecycle, memory-leak, security, or test-isolation defects introduced in changed code. Respect repository-local `detekt.yml`, `.editorconfig` (`ktlint_*`), and `lint.xml` configurations first when present; treat correctness/lifecycle/security violations as P0/P1 blocking and pure idiomatic polish as P2 advisory.

Before flagging non-local threading, lifecycle, or nullability issues, inspect surrounding callers, coroutine scopes, and Java/JNI boundaries via `file_read` or `code_search`. Do not duplicate `ktlint` or `detekt` formatting warnings unless they affect runtime behavior.

#### Null Safety, Platform Types & Type Contracts
- **Non-null assertion (`!!`) on reachable nullable inputs**: Flag `!!` on network DTOs, `Intent` extras, `Bundle` arguments, database cursors, or user input where `null` is reachable at runtime; prefer safe calls (`?.`), Elvis (`?:`), `requireNotNull(...)` with clear invariant messages, or early return.
- **Unchecked Java platform types (`T!`)**: Values returned from unannotated Java/Android SDK APIs (`Intent.getStringExtra`, `SharedPreferences.getString`, `Uri.parse`, Jackson/Gson reflection) can be `null` without compiler warnings; assign an explicit nullable type (`String?`) at the boundary.
- **`lateinit var` before initialization or after teardown**: Accessing `lateinit` properties (such as Fragment bindings or injected collaborators) before lifecycle initialization or after `onDestroyView()` throws `UninitializedPropertyAccessException`.
- **Mutable collections exposed from `data class` or `ViewModel` state**: Exposing `MutableList`/`MutableMap` or `Array` inside `data class` breaks `equals`/`hashCode` stability and unidirectional data flow (`StateFlow<UiState>`).

#### Coroutines, Structured Concurrency & `CancellationException`
- **Swallowing `CancellationException` (`P1` Blocking)**: Broad `try { ... } catch (e: Exception)` or `runCatching { ... }` around `suspend` calls (`withContext`, `delay`, Retrofit/Room suspend functions, `Flow.collect`) catches `CancellationException` and breaks structured cancellation. Always rethrow `if (e is CancellationException) throw e` (or `currentCoroutineContext().ensureActive()`). Never recommend bare `catch (e: Exception)` around suspend work.
- **Unstructured / leaking scopes**: Launching work on `GlobalScope` or constructing an unmanaged `CoroutineScope(Dispatchers.IO)` without cancelling it on teardown leaks coroutines and resources; bind to `viewModelScope`, `lifecycleScope`, or an injected lifecycle-managed scope.
- **Main-thread blocking I/O & `runBlocking`**: Calling `runBlocking` on `Dispatchers.Main` (risking ANRs/deadlocks) or performing disk, database, or synchronous network I/O without switching to `Dispatchers.IO`.
- **Exception propagation traps**: Passing `Job()` instead of `SupervisorJob()` to a top-level scope causes a single child failure to permanently cancel sibling launches; unhandled exceptions in `async` inside `coroutineScope` still fail the parent even if `.await()` is wrapped in `try/catch` unless scoped with `supervisorScope`.
- **Locks held across suspension points**: Holding `synchronized(...)` or `ReentrantLock` across `suspend` calls pins carrier threads and risks deadlocks; use `kotlinx.coroutines.sync.Mutex.withLock`.

#### Android Lifecycle, `Flow` Collection & Memory Leaks
- **Unsafe `Flow` collection in UI (`P1` Blocking)**: Collecting `Flow`/`StateFlow` directly inside `lifecycleScope.launch { flow.collect { ... } }` or `launchWhenStarted` keeps upstream producers (location, sensors, database observers) active while the app is in the background and risks crashes on stopped views. Use `viewLifecycleOwner.lifecycleScope.launch { viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) { ... } }` in Views/Fragments (note `viewLifecycleOwner`, never Activity/Fragment `this` in Fragments!) or `collectAsStateWithLifecycle()` in Jetpack Compose.
- **Context, View & Activity leaks**: Holding `Activity`, `Fragment`, `View`, `Drawable`, or Activity-scoped `Context` references inside a `ViewModel`, `companion object`, singleton, or long-lived callback leaks the entire view hierarchy across configuration changes; inject `Application` context only when strictly required.
- **Fragment view-binding retention**: Retaining a Fragment's `ViewBinding` reference past `onDestroyView()` leaks the detached view tree while the Fragment sits on the back stack.
- **Hot stream sharing (`stateIn` / `shareIn`)**: Using `SharingStarted.Eagerly` or `Lazily` for UI-bound `ViewModel` flows keeps upstream work alive indefinitely when no UI is visible; prefer `SharingStarted.WhileSubscribed(5_000)` unless background retention is intentional.
- **Process death & state restoration**: Storing critical user-navigation/form IDs solely in in-memory `ViewModel` fields without `SavedStateHandle` loses state on Android background process recreation.

#### Jetpack Compose State, Stability & Side Effects
- **Side effects inside `@Composable` body (`P1` Blocking)**: Launching coroutines, mutating state, registering listeners, or triggering navigation/analytics directly during composition runs repeatedly on every recomposition. Use `LaunchedEffect(key)` (keyed properly so stale parameters restart), `DisposableEffect(key)` (with `onDispose` cleanup), or `SideEffect`.
- **Unstable parameters & broken skippability**: Passing unstable mutable types (`MutableList`, plain `List` without strong skipping / `@Immutable` / `kotlinx.collections.immutable.ImmutableList`, or non-Compose-stable domain classes) to frequently recomposing subtrees causes unnecessary full recompositions.
- **Unremembered state & `derivedStateOf`**: Calling `mutableStateOf(...)` inside a `@Composable` without `remember` resets state on every recomposition; reading rapidly changing scroll/animation state directly instead of wrapping threshold calculations in `remember { derivedStateOf { ... } }` triggers frame drops.
- **Missing or unstable `LazyColumn`/`LazyRow` keys**: Omitting `key = { item.id }` on dynamic lists causes broken item animations, lost scroll/input state on insertion/deletion, and unnecessary slot recreation.

#### Android Security, Persistence & IPC
- **`PendingIntent` mutability (`P0`/`P1`)**: Creating `PendingIntent`s without explicit `PendingIntent.FLAG_IMMUTABLE` (or `FLAG_MUTABLE` only with an explicit package/component target when required for inline replies/bubbles) allows intent hijacking on Android 12+ or crashes at runtime.
- **Exported components & WebView hazards**: Activities, Services, BroadcastReceivers, or ContentProviders exported without permission/caller checks; `WebView` enabling `javaScriptEnabled = true` alongside `addJavascriptInterface` or universal file access on untrusted URLs; sensitive tokens stored in plaintext `SharedPreferences`/DataStore or logged via `Log.d`.
- **Room / SQLite transaction & migration safety**: Multi-step database read-modify-write sequences missing `@Transaction` / `db.withTransaction`; Room schema changes missing migration paths without intentional destructive fallback.

#### Official Kotlin & Android Kotlin Style Conventions
- **Official Kotlin Coding Conventions & Android Kotlin Style Guide**:
  - Prefer `val` over `var`, immutable collection interfaces (`List`, `Set`, `Map`) at API boundaries, expression `when` over cascading `if-else`, and `sealed interface` / `sealed class` hierarchies for exhaustive UI/domain results (`UiState`, `Result`) without catch-all `else` branches that hide newly added subtypes.
  - Close `Closeable` / `AutoCloseable` I/O streams, `Cursor`s, and `TypedArray`s via `.use { ... }`.
  - Keep scope functions (`let`, `run`, `apply`, `also`, `with`) shallow—avoid nested `it` shadowing across chained scope functions.
  - Inject `CoroutineDispatcher`s (`@IoDispatcher`, `@MainDispatcher`) rather than hardcoding `Dispatchers.IO` / `Dispatchers.Default` inside repositories and use cases.

#### Kotlin & Android Testing Correctness (`*Test.kt`)
- **Coroutines testing (`kotlinx-coroutines-test`)**: Use `runTest` with injected `TestDispatcher` (`StandardTestDispatcher` / `UnconfinedTestDispatcher`) and `MainDispatcherRule` (`Dispatchers.setMain` / `Dispatchers.resetMain` in teardown) rather than `Thread.sleep` or `runBlocking` with real wall-clock delays.
- **`Flow` & `StateFlow` assertions**: Verify emission sequences deterministically (e.g., Turbine `.test { awaitItem(); cancelAndIgnoreRemainingEvents() }` or background `backgroundScope.launch(UnconfinedTestDispatcher(testScheduler))`) so uncollected hot flows never hang `runTest`.
- **Anti-vacuity & MockK hygiene**: Never mock the class under test or assert solely on `verify` calls without asserting observable state/output; clear static/object mocks (`unmockkAll()` / `unmockkObject(...)`) in `@AfterEach` / `@After` so test pollution cannot leak across suites.
