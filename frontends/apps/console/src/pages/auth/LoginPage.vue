<template>
  <section class="page-stack">
    <div>
      <p class="eyebrow">Authentication</p>
      <h1>Login</h1>
      <p class="lede">
        Email OTP authentication will connect to the console auth API in the next implementation step.
      </p>
    </div>

    <form class="login-form">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" autocomplete="email" placeholder="name@example.com"/>
      <button type="button">Request OTP</button>
    </form>
  </section>
</template>
