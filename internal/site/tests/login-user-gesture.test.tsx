import { afterEach, beforeEach, describe, expect, mock, test } from "bun:test"
import { Window } from "happy-dom"
import { act, createElement } from "react"
import type { OAuth2AuthConfig } from "pocketbase"

const browser = new Window({ url: "https://hub.example.test/" })
// Bun does not populate the VM realm error constructor used by Happy DOM selectors.
Object.assign(browser, { SyntaxError })
for (const name of ["window", "document", "navigator", "HTMLElement", "Node", "Event", "MouseEvent"]) {
	Object.defineProperty(globalThis, name, { configurable: true, value: name === "window" ? browser : browser[name] })
}
Object.assign(globalThis, {
	IS_REACT_ACT_ENVIRONMENT: true,
	sessionStorage: browser.sessionStorage,
	localStorage: browser.localStorage,
})

const events: string[] = []
const errors: unknown[] = []
const authenticated: boolean[] = []
let options: OAuth2AuthConfig | undefined
let finishOAuth: (() => void) | undefined
let popupBlocked = false
let duringClick = false
const popup = { location: { href: "" } }
const authStore = { isValid: false, save: () => {} }
const users = {
	authWithOAuth2(config: OAuth2AuthConfig) {
		events.push("oauth")
		options = config
		config.urlCallback?.(
			"https://auth.example.test/authorize?redirect_uri=https%3A%2F%2Fhub.example.test%2Fapi%2Foauth2-redirect"
		)
		return new Promise<void>((resolve) => {
			finishOAuth = () => {
				authStore.isValid = true
				resolve()
			}
		})
	},
	authRefresh() {
		events.push("refresh")
		return Promise.resolve({ token: "", record: null })
	},
}
mock.module("@/lib/utils", () => ({ cn: (...values: unknown[]) => values.filter(Boolean).join(" ") }))
mock.module("@/lib/api", () => ({ pb: { collection: () => users, authStore } }))
mock.module("@/lib/stores", () => ({ $authenticated: { set: (value: boolean) => authenticated.push(value) } }))
mock.module("@/components/ui/button", () => ({ buttonVariants: () => "" }))
mock.module("@/components/ui/dialog", () => ({
	Dialog: () => null,
	DialogContent: () => null,
	DialogHeader: () => null,
	DialogTitle: () => null,
	DialogTrigger: () => null,
}))
mock.module("@/components/ui/input", () => ({
	Input: (props: React.ComponentProps<"input">) => createElement("input", props),
}))
mock.module("@/components/ui/label", () => ({
	Label: (props: React.ComponentProps<"label">) => createElement("label", props),
}))
mock.module("@/components/router", () => ({
	$router: {},
	Link: () => null,
	basePath: "/",
	prependBasePath: (value: string) => value,
}))
mock.module("@/components/ui/use-toast", () => ({ toast: (value: unknown) => errors.push(value) }))
mock.module("@/components/login/otp-forms", () => ({ OtpInputForm: () => null }))
mock.module("@lingui/core/macro", () => ({ t: (strings: TemplateStringsArray) => strings.join("") }))
mock.module("@lingui/react/macro", () => ({ Trans: ({ children }: { children: unknown }) => children }))

const { createRoot } = await import("react-dom/client")
const { UserAuthForm } = await import("../src/components/login/auth-form")
const provider = {
	name: "oidc",
	displayName: "ZITADEL",
	state: "synthetic-state",
	authURL: "https://auth.example.test/authorize",
	codeVerifier: "synthetic-verifier",
	codeChallenge: "synthetic-challenge",
	codeChallengeMethod: "S256",
}
const methods = {
	password: { enabled: false, identityFields: ["email"] },
	oauth2: { enabled: true, providers: [provider] },
	otp: { enabled: false, duration: 0 },
	mfa: { enabled: false, duration: 0 },
}
let container: HTMLDivElement
let root: ReturnType<typeof createRoot>

beforeEach(async () => {
	events.length = 0
	errors.length = 0
	authenticated.length = 0
	options = undefined
	finishOAuth = undefined
	popupBlocked = false
	popup.location.href = ""
	authStore.isValid = false
	browser.sessionStorage.clear()
	browser.localStorage.clear()
	Object.assign(globalThis, { BESZEL: { OAUTH_DISABLE_POPUP: false } })
	Object.assign(browser, {
		open: () => {
			events.push(duringClick ? "gesture-popup" : "automatic-popup")
			return popupBlocked ? null : popup
		},
	})
	container = browser.document.createElement("div") as unknown as HTMLDivElement
	browser.document.body.append(container)
	root = createRoot(container)
	await act(() => {
		root.render(createElement(UserAuthForm, { isFirstRun: false, authMethods: methods }))
	})
})

afterEach(async () => {
	await act(async () => root.unmount())
	container.remove()
})

function button() {
	const result = container.querySelector("button")
	if (!result) throw new Error("Provider button missing")
	expect(result.textContent).toContain("ZITADEL")
	return result
}

async function click() {
	await act(() => {
		duringClick = true
		try {
			button().dispatchEvent(new browser.MouseEvent("click", { bubbles: true }) as unknown as MouseEvent)
		} finally {
			duringClick = false
		}
	})
}

describe("provider-only login user gesture", () => {
	test("mount stays ready without an automatic OAuth attempt or permanently busy button", async () => {
		await act(async () => {
			await new Promise((resolve) => setTimeout(resolve, 400))
		})
		expect(events).toEqual([])
		expect(button().disabled).toBe(false)
		expect(container.querySelector('input[type="password"]')).toBeNull()
	})

	test("an explicit click opens the popup synchronously before the existing OAuth flow", async () => {
		await click()
		expect(events).toEqual(["gesture-popup", "oauth"])
		expect(options?.provider).toBe("oidc")
		expect(popup.location.href).toBe(
			"https://auth.example.test/authorize?redirect_uri=https%3A%2F%2Fhub.example.test%2Fapi%2Foauth2-redirect"
		)
		expect(button().disabled).toBe(true)
		await act(async () => finishOAuth?.())
		expect(authenticated).toEqual([true])
		expect(button().disabled).toBe(false)
		expect(errors).toEqual([])
	})

	test("a blocked popup reports the existing error, leaves the button enabled and permits retry", async () => {
		popupBlocked = true
		await click()
		expect(events).toEqual(["gesture-popup"])
		expect(options).toBeUndefined()
		expect(errors).toHaveLength(1)
		expect(button().disabled).toBe(false)
		popupBlocked = false
		await click()
		expect(events).toEqual(["gesture-popup", "gesture-popup", "oauth"])
		expect(button().disabled).toBe(true)
		await act(async () => finishOAuth?.())
		expect(button().disabled).toBe(false)
	})
})
