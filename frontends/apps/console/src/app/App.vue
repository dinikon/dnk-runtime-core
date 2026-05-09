<template>
  <div class="console-shell">
    <header class="console-header">
      <RouterLink class="brand" to="/">DNK Console</RouterLink>
      <nav class="main-nav" aria-label="Primary">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/login">Login</RouterLink>
      </nav>
    </header>

    <main class="console-main">
      <RouterView/>
    </main>
  </div>
</template>
