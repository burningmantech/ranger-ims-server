import {test, expect, Page} from "@playwright/test";

const username = "Hardware";

function randomName(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

async function login(page: Page): Promise<void> {
  await page.goto("http://localhost:8080/ims/auth/logout");
  await page.goto("http://localhost:8080/ims/app/");
  await page.getByRole("button", { name: "Log In" }).click();
  await page.getByPlaceholder("name@example.com").click();
  await page.getByPlaceholder("name@example.com").fill(username);
  await page.getByPlaceholder("Password").fill(username);
  await page.getByPlaceholder("Password").press("Enter");
}

async function adminPage(page: Page): Promise<void> {
  await maybeOpenNav(page);
  await page.getByRole("button", { name: "Event" }).click();
  await page.getByRole("button", { name: username }).click();
  await page.getByRole("link", { name: "Admin" }).click();
}

async function incidentTypePage(page: Page): Promise<void> {
  await adminPage(page);
  await page.getByRole("link", { name: "Incident Types" }).click();
}

async function eventsPage(page: Page): Promise<void> {
  await adminPage(page);
  await page.getByRole("link", { name: "Events" }).click();
}

async function addIncidentType(page: Page, incidentType: string): Promise<void> {
  await incidentTypePage(page);
  await page.getByPlaceholder("Chooch").fill(incidentType);
  await page.getByPlaceholder("Chooch").press("Enter");
}

async function addEvent(page: Page, eventName: string): Promise<void> {
  await eventsPage(page);
  await page.getByPlaceholder("Burn-A-Matic 3000").fill(eventName);
  await page.getByPlaceholder("Burn-A-Matic 3000").press("Enter");

  await expect(page.getByText(`Access for ${eventName} (readers)`)).toBeVisible();
  await expect(page.getByText(`Access for ${eventName} (writers)`)).toBeVisible();
  await expect(page.getByText(`Access for ${eventName} (reporters)`)).toBeVisible();
}

async function addWriter(page: Page, eventName: string, writer: string): Promise<void> {
  await eventsPage(page);

  const writers = page.locator("div.card").filter({has: page.getByText(`Access for ${eventName} (writers)`)});

  await writers.getByRole("textbox").fill(writer);
  await writers.getByRole("textbox").press("Enter");
  await expect(writers.getByText(writer)).toBeVisible();
}

async function maybeOpenNav(page: Page): Promise<void> {
  const toggler = page.getByLabel("Toggle navigation");
  if (await toggler.isVisible() && (await toggler.getAttribute("aria-expanded")) === "false") {
    await page.locator(".navbar-toggler").click();
  }
}

test("themes", async ({ page }) => {
  await page.goto("http://localhost:8080/ims/app/");

  await maybeOpenNav(page);
  await page.getByTitle("Color scheme").getByRole("button").click();
  await page.getByRole('button', { name: 'Dark' }).click();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("dark");

  await page.reload();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("dark");
  await maybeOpenNav(page);
  await page.getByTitle("Color scheme").getByRole("button").click();
  await page.getByRole('button', { name: 'Light' }).click();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("light");

  await page.reload();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("light");
})

test("admin_incident_types", async ({ page }) => {
  await login(page);

  const incidentType: string = randomName("type");
  await addIncidentType(page, incidentType);

  await incidentTypePage(page);

  const newLi = page.locator(`li[value="${incidentType}"]`);
  await expect(newLi).toBeVisible();
  await expect(newLi.getByRole("button", {name: "Active"})).toBeVisible();
  await expect(newLi.getByRole("button", {name: "Hidden"})).toBeHidden();

  await newLi.getByRole("button", {name: "Active"}).click();
  await expect(newLi.getByRole("button", {name: "Active"})).toBeHidden();
  await expect(newLi.getByRole("button", {name: "Hidden"})).toBeVisible();
});

test("admin_events", async ({ page }) => {
  await login(page);

  const eventName: string = randomName("event");
  await addEvent(page, eventName);
  await addWriter(page, eventName, "person:SomeGuy");

  let writers = page.locator("div.card").filter({has: page.getByText(`Access for ${eventName} (writers)`)});
  await writers.locator("select").selectOption("On-Site");
  await page.reload();
  await expect(writers).toBeVisible();
  await expect(writers.getByText("person:SomeGuy")).toBeVisible();
  await expect(writers.locator("select")).toHaveValue("onsite");
})

test("incidents", async ({ page, browser }) => {
  test.slow();

  await login(page);
  const eventName: string = randomName("event");
  await addEvent(page, eventName);
  await addWriter(page, eventName, "person:" + username);
  await page.close();

  for (let i = 0; i < 5; i++) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage()
    await login(page);

    await page.goto(`http://localhost:8080/ims/app/events/${eventName}/incidents/`);
    const incidentsPage = page;
    const page1Promise = incidentsPage.waitForEvent('popup');
    await incidentsPage.getByRole('button', { name: 'New' }).click();
    const incidentPage = await page1Promise;

    await expect(incidentPage.getByLabel("IMS #")).toHaveText("(new)");
    const incidentSummary = randomName("summary");
    await incidentPage.getByLabel('Summary').fill(incidentSummary);
    await incidentPage.getByLabel('Summary').press('Tab');
    // wait for the new incident to be persisted
    await expect(incidentPage.getByLabel("IMS #")).toHaveText(/^\d+$/);

    // check that the BroadcastChannel update to the first page worked
    await expect(incidentsPage.getByText(incidentSummary)).toBeVisible();

    // change the summary
    const newIncidentSummary = incidentSummary + " with suffix";
    await incidentPage.getByLabel('Summary').fill(newIncidentSummary);
    await incidentPage.getByLabel('Summary').press('Tab');
    // check that the BroadcastChannel update to the first page worked
    await expect(incidentsPage.getByText(newIncidentSummary)).toBeVisible();

    await incidentPage.getByLabel('State').selectOption('on_hold');
    await incidentPage.getByLabel('State').press("Tab");

    async function addType(page: Page, type: string): Promise<void> {
      await page.getByLabel('Add Incident Type').fill(type);
      await page.getByLabel('Add Incident Type').press('Tab');
      await expect(
          page.locator("div.card").filter(
              {has: page.getByText("Incident Types")}
          ).locator('li', {hasText: type})).toBeVisible();
    }

    await addType(incidentPage, 'Admin');
    await addType(incidentPage, 'Junk');

    async function addRanger(page: Page, rangerName: string): Promise<void> {
      await page.getByLabel("Add Ranger Handle").fill(rangerName);
      await page.getByLabel("Add Ranger Handle").press('Tab');
      await expect(page.locator('li', {hasText: rangerName})).toBeVisible();
    }

    await addRanger(incidentPage, 'Defect');
    await addRanger(incidentPage, 'Irate');
    await addRanger(incidentPage, 'Loosy');
    await addRanger(incidentPage, 'Parenthetical');

    await incidentPage.getByLabel('Location name').click();
    await incidentPage.getByLabel('Location name').fill('Somewhere');
    await incidentPage.getByLabel('Location name').press('Tab');
    await incidentPage.getByLabel('Incident location address radial hour').selectOption('03');
    await incidentPage.getByLabel('Incident location address radial minute').selectOption('15');
    await incidentPage.getByLabel('Additional location description').click();
    await incidentPage.getByLabel('Additional location description').fill('other there');
    await incidentPage.getByLabel('Additional location description').press('Tab');
    const reportEntry = `This is some text - ${randomName("text")}`;
    await incidentPage.getByLabel('New report entry text').fill(reportEntry);
    await incidentPage.getByLabel('Submit report entry').click();

    await expect(incidentPage.getByText(reportEntry)).toBeVisible();

    await incidentPage.close();
    await incidentsPage.close();
  }
})
