import {test, expect, Page} from "@playwright/test";

const username = "Hardware";

function randomName(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

async function login(page: Page): Promise<void> {
  await page.goto("http://localhost:8080/ims/app/");
  // wait for one of the buttons to be shown
  await expect(page.getByRole("button", { name: /^Log (In|Out)$/ })).toBeVisible();
  if (await page.getByRole("button", { name: "Log In" }).isVisible()) {
    await page.getByRole("button", { name: "Log In" }).click();
    await page.getByPlaceholder("name@example.com").click();
    await page.getByPlaceholder("name@example.com").fill(username);
    await page.getByPlaceholder("Password").fill(username);
    await page.getByPlaceholder("Password").press("Enter");
  }
  await expect(page.getByRole("button", { name: "Log Out" })).toBeVisible();
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
  await expect(writers.getByText(writer)).toBeVisible({timeout: 5000});
}

async function maybeOpenNav(page: Page): Promise<void> {
  const toggler = page.getByLabel("Toggle navigation");
  await expect(async (): Promise<void> => {
    if (await toggler.isVisible() && (await toggler.getAttribute("aria-expanded")) === "false") {
      await page.locator(".navbar-toggler").click();
      expect(toggler.getAttribute("aria-expanded")).toEqual("true");
    }
  }).toPass();
}

test("themes", async ({ page }) => {
  await page.goto("http://localhost:8080/ims/app/");

  await maybeOpenNav(page);
  await page.getByTitle("Color scheme").getByRole("button").click();
  await page.getByRole("button", { name: "Dark" }).click();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("dark");

  await page.reload();
  expect(await page.locator("html").getAttribute("data-bs-theme")).toEqual("dark");
  await maybeOpenNav(page);
  await page.getByTitle("Color scheme").getByRole("button").click();
  await page.getByRole("button", { name: "Light" }).click();
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

test("admin_events", async ({ browser }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage()
  await login(page);

  const eventName: string = randomName("event");
  await addEvent(page, eventName);
  await addWriter(page, eventName, "person:SomeGuy");

  let writers = page.locator("div.card").filter({has: page.getByText(`Access for ${eventName} (writers)`)});
  // it's hard to tell on the client side when this has completed, hence the toPass block below
  await writers.locator("select").selectOption("On-Site");

  const page2 = await ctx.newPage();
  await login(page2);
  await eventsPage(page2);
  await expect(async (): Promise<void> => {
    let writers = page2.locator("div.card").filter({has: page2.getByText(`Access for ${eventName} (writers)`)});
    await expect(writers).toBeVisible();
    await expect(writers.getByText("person:SomeGuy")).toBeVisible();
    await expect(writers.locator("select")).toHaveValue("onsite");
  }).toPass();
})

test("incidents", async ({ page, browser }) => {
  test.slow();

  // make a new event with a writer
  await login(page);
  const eventName: string = randomName("event");
  await addEvent(page, eventName);
  await addWriter(page, eventName, "person:" + username);

  // check that we can navigate to the incidents page for that event
  await page.goto("http://localhost:8080/ims/app/");
  await maybeOpenNav(page);
  await page.getByRole("button", {name: "Event"}).click();
  await page.getByRole("link", {name: eventName}).click();
  expect(page.url()).toBe(`http://localhost:8080/ims/app/events/${eventName}/incidents/`);

  await page.close();

  for (let i = 0; i < 3; i++) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage()
    await login(page);

    await page.goto(`http://localhost:8080/ims/app/events/${eventName}/incidents/`);
    const incidentsPage = page;
    const page1Promise = incidentsPage.waitForEvent("popup");
    await incidentsPage.getByRole("button", {name: "New"}).click();
    const incidentPage = await page1Promise;

    await expect(incidentPage.getByLabel("IMS #")).toHaveText("(new)");
    const incidentSummary = randomName("summary");
    await incidentPage.getByLabel("Summary").fill(incidentSummary);
    await incidentPage.getByLabel("Summary").press("Tab");
    // wait for the new incident to be persisted
    await expect(incidentPage.getByLabel("IMS #")).toHaveText(/^\d+$/);

    // check that the BroadcastChannel update to the first page worked
    await expect(incidentsPage.getByText(incidentSummary)).toBeVisible();

    // change the summary
    const newIncidentSummary = incidentSummary + " with suffix";
    await incidentPage.getByLabel("Summary").fill(newIncidentSummary);
    await incidentPage.getByLabel("Summary").press("Tab");
    // check that the BroadcastChannel update to the first page worked
    await expect(incidentsPage.getByText(newIncidentSummary)).toBeVisible();

    await incidentPage.getByLabel("State").selectOption("on_hold");
    await incidentPage.getByLabel("State").press("Tab");

    // add several incident types to the incident
    {
      async function addType(page: Page, type: string): Promise<void> {
        await page.getByLabel("Add Incident Type").fill(type);
        await page.getByLabel("Add Incident Type").press("Tab");

        await expect(
            page.locator("div.card").filter(
                {has: page.getByText("Incident Types")}
            ).locator("li", {hasText: type})).toBeVisible({timeout: 5000});
        await expect(page.getByLabel("Add Incident Type")).toHaveValue("");
      }

      await addType(incidentPage, "Admin");
      await addType(incidentPage, "Junk");
    }

    // add several Rangers to the incident
    {
      async function addRanger(page: Page, rangerName: string): Promise<void> {
        await page.getByLabel("Add Ranger Handle").fill("");
        await page.getByLabel("Add Ranger Handle").press("Tab");
        await page.getByLabel("Add Ranger Handle").fill(rangerName);
        await page.getByLabel("Add Ranger Handle").press("Tab");
        await expect(page.locator("li", {hasText: rangerName})).toBeVisible({timeout: 5000});
        await expect(page.getByLabel("Add Ranger Handle")).toHaveValue("");
      }

      await addRanger(incidentPage, "Defect");
      await addRanger(incidentPage, "Irate");
      await addRanger(incidentPage, "Loosy");
      await addRanger(incidentPage, "Parenthetical");
    }

    // add location details
    {
      await incidentPage.getByLabel("Location name").click();
      await incidentPage.getByLabel("Location name").fill("Somewhere");
      await incidentPage.getByLabel("Location name").press("Tab");
      await incidentPage.getByLabel("Incident location address radial hour").selectOption("03");
      await incidentPage.getByLabel("Incident location address radial minute").selectOption("15");
      await incidentPage.getByLabel("Additional location description").click();
      await incidentPage.getByLabel("Additional location description").fill("other there");
      await incidentPage.getByLabel("Additional location description").press("Tab");
    }
    // add a report entry
    const reportEntry = `This is some text - ${randomName("text")}`;
    {
      await incidentPage.getByLabel("New report entry text").fill(reportEntry);
      await incidentPage.getByLabel("Submit report entry").click();
      await expect(incidentPage.getByText(reportEntry)).toBeVisible();
    }
    // strike the entry, verified it's stricken
    {
      await incidentPage.getByText(reportEntry).hover();
      await incidentPage.getByRole("button", {name: "Strike"}).click();
      await expect(incidentPage.getByText(reportEntry)).toBeHidden();
    }
    // but the entry is shown when the right checkbox is ticked
    {
      await incidentPage.getByLabel("Show history and stricken").check();
      await expect(incidentPage.getByText(reportEntry)).toBeVisible();
    }
    // unstrike the entry and see it return to the default view
    {
      await incidentPage.getByText(reportEntry).hover();
      await incidentPage.getByRole("button", {name: "Unstrike"}).click();
      await incidentPage.getByLabel("Show history and stricken").uncheck();
      await expect(incidentPage.getByText(reportEntry)).toBeVisible();
    }

    // try searching for the incident by its report text
    {
      await incidentsPage.getByRole("searchbox").fill(reportEntry);
      await incidentsPage.getByRole("searchbox").press("Enter");
      await expect(incidentsPage.getByText(newIncidentSummary)).toBeVisible();
      await incidentsPage.getByRole("searchbox").fill("The wrong text!");
      await incidentsPage.getByRole("searchbox").press("Enter");
      await expect(incidentsPage.getByText(newIncidentSummary)).toBeHidden();
      await incidentsPage.getByRole("searchbox").clear();
      await incidentsPage.getByRole("searchbox").press("Enter");
      await expect(incidentsPage.getByText(newIncidentSummary)).toBeVisible();
    }

    // close the incident and see it disappear from the default Incidents page view
    {
      await incidentPage.getByLabel("State").selectOption("closed");
      await incidentPage.getByLabel("State").press("Tab");
      await expect(incidentsPage.getByText(newIncidentSummary)).toBeHidden();
    }

    await incidentPage.close();
    await incidentsPage.close();
  }
})
