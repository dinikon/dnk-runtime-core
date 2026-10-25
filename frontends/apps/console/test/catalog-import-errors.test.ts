import { test } from "node:test";
import assert from "node:assert/strict";
import { AxiosError, AxiosHeaders } from "axios";
import { getApiErrorMessage } from "../src/app/providers/http/errors.ts";

function responseError(data: unknown, status = 409): AxiosError {
  return new AxiosError(
    "Request failed",
    "ERR_BAD_REQUEST",
    undefined,
    undefined,
    {
      status,
      statusText: "Conflict",
      headers: {},
      config: { headers: new AxiosHeaders() },
      data,
    },
  );
}

test("second import shows the actual Catalog conflict instead of a generic launch failure", () => {
  const message = "В этом рабочем пространстве уже выполняется импорт.";
  const error = responseError({ detail: { message, fields: [] } });
  assert.equal(
    getApiErrorMessage(error, "Не удалось запустить импорт."),
    message,
  );
});

test("existing plain and string-detail HTTP messages still display", () => {
  for (const data of [
    "Источник недоступен",
    { detail: "Источник недоступен" },
  ]) {
    assert.equal(
      getApiErrorMessage(responseError(data), "Ошибка"),
      "Источник недоступен",
    );
  }
});

test("validation arrays, missing messages and transport failures retain a readable fallback", () => {
  for (const data of [
    null,
    {},
    { detail: [] },
    { detail: { fields: ["sku"] } },
    { detail: { message: " " } },
    { detail: { message: 409 } },
  ]) {
    assert.equal(
      getApiErrorMessage(responseError(data), "Ошибка запуска"),
      "Ошибка запуска",
    );
  }
  assert.equal(
    getApiErrorMessage(new AxiosError("Network Error"), "Ошибка сети"),
    "Ошибка сети",
  );
  assert.equal(
    getApiErrorMessage(new Error("Internal failure"), "Ошибка запуска"),
    "Ошибка запуска",
  );
});
