/** tcapp browser user interface.
 */
var app = angular.module("tcappApp", ["ui.bootstrap", "tcappControllers"]);
var tcappControllers = angular.module("tcappControllers", []);


app.directive('djuploadSuccess', function() {
  return {
    scope: {
      docs: '=docs'
    },
    link:  function link(scope, element) {
      element.bind('djupload.success', function(event, location) {
        scope.$apply(function() { scope.$parent.djuploadSuccess(scope.docs, location); });
      });
    }
  }
});


tcappControllers.controller("tcappCtrl",
    ["$scope", "$timeout", "$http", "settings",
     function($scope, $timeout, $http, settings) {
         //"use strict";

    $scope.djuploadSuccess = function(docs, location) {
        docs.push({
            printable_name: "recent upload",
            url: location});
    };

    $scope.QUESTIONS = ['selfemployed', 'employee',
            'disability', 'publicassistance', 'socialsecurity',
            'supplemental', 'unemployment', 'veteran', 'others',
            'support_payments', 'trusts', 'unearned', 'studentfinancialaid',
            // assets
            'fiduciaries', 'life_insurances'];

    // XXX AngularJS constants should be defined elsewhere?
    $scope.MARITAL_STATUS_NONE_OF_THE_ABOVE = 0;
    $scope.MARRIED_FILE_JOINTLY = 1;
    $scope.SEPARATED = 2;
    $scope.LEGALY_SEPARATED = 3;

    $scope.VERIFIED_TENANT = "tenant";
    $scope.VERIFIED_EMPLOYER = "employer";
    $scope.VERIFIED_YEAR_TO_DATE = "year-to-date";
    $scope.VERIFIED_PERIOD_TO_DATE = "period-to-date";
    $scope.VERIFIED_TAX_RETURN = "tax-return";

    $scope.OTHER = "other";
    $scope.HOURLY = "hourly";
    $scope.DAILY = "daily";
    $scope.WEEKLY = "weekly";
    $scope.BI_WEEKLY = "bi-weekly";
    $scope.SEMI_MONTHLY = "semi-monthly";
    $scope.MONTHLY = "monthly";
    $scope.YEARLY = "yearly";

    $scope.PERIOD = {
        "other": "other",
        "hourly": "hourly",
        "daily": "daily",
        "weekly": "weekly",
        "bi-weekly": "bi-weekly",
        "semi-monthly": "semi-monthly",
        "monthly": "monthly",
        "yearly": "yearly"
    };

    $scope.asPeriodText = function(periodNum) {
        return $scope.PERIOD[periodNum];
    };

    $scope.asPeriodNouns = function(periodNum) {
        var PERIOD_NOUNS = {
            "other": "other",
            "hourly": "hours",
            "daily": "days",
            "weekly": "weeks",
            "bi-weekly": "bi-weeklies",
            "semi-monthly": "1/2-months",
            "monthly": "months",
            "yearly": "out"
        };
        return PERIOD_NOUNS[periodNum];
    };

    $scope.periodPerNatural = function(period) {
        var periodNum = period;
        if( periodNum === $scope.DAILY ) {
            return "days per week";
        }
        return "hours per week";
    };

    $scope.naturalPerYear = function(period) {
        var periodNum = period;
        if( periodNum === $scope.OTHER ) {
            return "days per year";
        } else if( periodNum === $scope.HOURLY
            || periodNum === $scope.DAILY
            || periodNum === $scope.WEEKLY ) {
            return "weeks per year";
        } else if ( periodNum === $scope.BI_WEEKLY ) {
            return "bi-weeklies per year";
        } else if ( periodNum === $scope.SEMI_MONTHLY ) {
            return "1/2-months per year";
        } else if ( periodNum === $scope.MONTHLY ) {
            return "months per year";
        } else if ( periodNum === $scope.YEARLY ) {
            return "yearly fraction";
        }
        return "";
    };

    $scope.naturalAvgPerYear = function(period) {
        var periodNum = period;
        if( periodNum === $scope.HOURLY ) {
            return 52;
        } else if ( periodNum === $scope.DAILY ) {
            return 52;
        } else if ( periodNum === $scope.WEEKLY ) {
            return 52;
        } else if ( periodNum === $scope.BI_WEEKLY ) {
            return 26;
        } else if ( periodNum === $scope.SEMI_MONTHLY ) {
            return 26;
        } else if ( periodNum === $scope.MONTHLY ) {
            return 12;
        } else if ( periodNum === $scope.YEARLY ) {
            return 1;
        }
        // number of days taking leap year into account
        var year = (new Date()).getFullYear();
        return ((year % 4) != 0 )
            || ( ((year % 100) == 0) && ((year % 400) != 0) ) ? 365 : 366;
    };

    $scope.nbDays = function(income) {
        // last day of period is included.
        return moment(income.ends_at).diff(income.starts_at, "days") + 1;
    };

    $scope.periodSelectDisabled = function(income) {
        return ( verified === $scope.VERIFIED_YEAR_TO_DATE
            || verified === $scope.VERIFIED_PERIOD_TO_DATE
            || verified === $scope.VERIFIED_TAX_RETURN );
    }

    $scope.OWNER = 0;
    $scope.NORMAL_SALE = 1;
    $scope.FORECLOSURE = 2;
    $scope.SHORT_SALE = 3;

    // Relation to head
    $scope.HEAD_OF_HOUSEHOLD = "HEAD";
    $scope.CHILD = "Child";

    $scope.CATEGORY = {
        "regular": "regular",
        "overtime": "overtime",
        "shift-differential": "shift differential",
        "tips": "tips",
        "commission": "commission",
        "bonuses": "bonuses",
        "other": "other"
    };

    $scope.GIFTS = "gifts";
    $scope.UNEARNED = "unearned income from family members age 17 or under";

    $scope.BANK_CATEGORY = {
        "checking": "Checking",
        "savings": "Savings",
        "certificate of deposit": "Certificates of Deposit",
        "money market": "Money Market",
        "revokable trust": "Revocable trust",
        "IRA": "IRA",
        "lump sump pension": "Lump Sum Pension",
        "Keogh account": "Keogh account",
        "401K": "401K",
        "brokerage": "Brokerage"
    };

    $scope.dateOptions = {
        formatYear: 'yyyy',
        startingDay: 1,
        minDate: new Date('2015-01-01'),
        initDate: moment().toDate()
    };
    $scope.format = "MM-dd-yyyy";

    $scope.opened = {};

    $scope.effectiveDate = {
        val: settings.fields.effective_date ?
            moment(settings.fields.effective_date).toDate() : new Date(),
        opened: false};
    $scope.moveInDate = {
        val: settings.fields.move_in_date ?
            moment(settings.fields.move_in_date).toDate() : new Date(),
        opened: false};
    var dateOfBirth = moment($("#id_date_of_birth").val());
    $scope.date_of_birth = {
        val: dateOfBirth ? dateOfBirth.toDate() : new Date(),
        opened: false};

    $scope.open = function($event, datePicker) {
        $event.preventDefault();
        $event.stopPropagation();
        datePicker.opened = true;
    };

    $scope.openDatePicker = function($event, datePicker) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.opened[datePicker] = true;
    };

    $scope.nb_bedrooms = (
        settings.fields.nb_bedrooms ?
            settings.fields.nb_bedrooms : 0);
    $scope.federal_income_restriction = (
        settings.fields.federal_income_restriction ?
            settings.fields.federal_income_restriction : 0);
    $scope.monthly_rent = (
        settings.fields.monthly_rent ?
            settings.fields.monthly_rent / 100 : 0);
    $scope.federal_rent_restriction = (
        settings.fields.federal_rent_restriction ?
            settings.fields.federal_rent_restriction : 0);
    $scope.bond_rent_restriction = (
        settings.fields.bond_rent_restriction ?
            settings.fields.bond_rent_restriction : 0);
    $scope.federal_rent_assistance = (
        settings.fields.federal_rent_assistance ?
            settings.fields.federal_rent_assistance  / 100 : 0);
    $scope.non_federal_rent_assistance = (
        settings.fields.non_federal_rent_assistance ?
            settings.fields.non_federal_rent_assistance  / 100 : 0);

    $scope.other_certification_text = ""; // XXX based on certification_type.

    $scope.federal_income_restriction_other_text = (
        ($scope.federal_income_restriction !== 50
         && $scope.federal_income_restriction !== 60) ?
        $scope.federal_income_restriction : "");
    $scope.federal_rent_restriction_other_text = (
        ($scope.federal_rent_restriction !== 50
         && $scope.federal_rent_restriction !== 60) ?
        $scope.federal_rent_restriction : "");

    $scope.is_other_certification = function() {
        return $scope.other_certification_text.length > 0;
    };

    $scope.is_federal_income_restriction_other = function() {
        var length = $scope.federal_income_restriction_other_text.length;
        if( typeof(length) === "undefined" ) {
            var result = ($scope.federal_income_restriction_other_text !== 50
                    && $scope.federal_income_restriction_other_text !== 60);
            return result;
        }
        return length > 0;
    };

    $scope.is_federal_rent_restriction_other = function() {
        var length = $scope.federal_rent_restriction_other_text.length;
        if( typeof length === "undefined" ) {
            return ($scope.federal_rent_restriction_other_text !== 50
                    && $scope.federal_rent_restriction_other_text !== 60);
        }
        return length > 0;
    };

    /** Returns the annual income limits in dollars
     */
    $scope.lihtc_income_limit = function() {
        return $scope.federal_income_restriction * settings.limits.income_100 / 10000;
    };

    $scope.bond_income_limit = function() {
        // XXX Is it the correct formula?
        return $scope.federal_income_restriction * settings.limits.income_100 / 10000;
    };

    $scope.is_eligible = function(total_income) {
        return total_income <= Math.round($scope.lihtc_income_limit() * 100);
    };

    $scope.is_eligible_140 = function(total_income) {
        return total_income <= ($scope.lihtc_income_limit() * 140 / 100);
    };

    /** Returns the monthly utility allowance in dollars
     */
    $scope.utility_allowance = function() {
        var result = settings.limits.rent_100[$scope.nb_bedrooms].utility_allowance;
        if( !result ) { result = 0; }
        return result / 100;
    };

    /** Returns the monthly non optional charges in dollars
     */
    $scope.non_optional_charges = function() {
        var result = settings.limits.rent_100[$scope.nb_bedrooms].non_optional_charges;
        if( !result ) { result = 0; }
        return  result / 100;
    };

    /** Returns the gross monthly rent for the unit in dollars
     */
    $scope.gross_monthly_rent_for_unit = function() {
        var utilityAllowance
            = settings.limits.rent_100[$scope.nb_bedrooms].utility_allowance;
        if( !utilityAllowance ) { utilityAllowance = 0; }
        var nonOptionalCharges
            = settings.limits.rent_100[$scope.nb_bedrooms].non_optional_charges;
        if( !nonOptionalCharges ) { nonOptionalCharges = 0; }
        return (Math.round($scope.monthly_rent * 100)
            + utilityAllowance + nonOptionalCharges)
            / 100;
    };

    /** Returns the rent limits in dollars
     */
    $scope.lihtc_rent_limit = function() {
        var rent_limit = $scope.federal_rent_restriction
            * settings.limits.rent_100[$scope.nb_bedrooms].maximum_federal_lihtc_rent
            / 10000;
        return Math.round(rent_limit);
    };

    $scope.bond_rent_limit = function() {
        // XXX Is it the correct computation?
        return $scope.lihtc_rent_limit();
    };


    /** Returns the rent limit in dollars
     */
    $scope.total_rent_assistance = function() {
        return $scope.federal_rent_assistance
            + $scope.non_federal_rent_assistance;
    };

    $scope.is_less_than_rent_limit = function() {
        return ($scope.gross_monthly_rent_for_unit()
                - $scope.total_rent_assistance()) <= $scope.lihtc_rent_limit();
    };


    // Wizard
    // ------

    $scope.hasImplicitPeriod = function(source) {
        return ((typeof source.verified === "undefined")
            || (source.verified === $scope.VERIFIED_YEAR_TO_DATE)
            || (source.verified === $scope.VERIFIED_PERIOD_TO_DATE)
            || (source.verified === $scope.VERIFIED_TAX_RETURN));
    };

    $scope.hasPeriodRates = function(source, account) {
        if( !(typeof account === "undefined") ) {
            var period = account.period;
            return (period === $scope.HOURLY || period === $scope.DAILY);
        }
        if( source.incomes ) {
            for( var i = 0; i < source.incomes.length; ++i ) {
                var period = source.incomes[i].period;
                if(period === $scope.HOURLY || period === $scope.DAILY) { return true; }
            }
        }
        return false;
    };

    // Methods dealing with student status
    // -----------------------------------
    $scope.isFullTimeStudent = function(student) {
        return student.current || student.past || student.future;
    }

    $scope.studentFinancialAid = function(student) {
        if( typeof student === "undefined"
            || typeof student.financial_aid === "undefined"
            || typeof student.financial_aid.amount === "undefined" ) {
            return 0;
        }
        var financialAidMonthlyAmount = student.financial_aid.amount;
        var costOfTuitionMonthlyAmount = student.cost_of_tuition.amount;
        return financialAidMonthlyAmount - costOfTuitionMonthlyAmount;
    };

    $scope.studentLowerBound = function() {
        return moment().startOf('year').format("MMMM YYYY");
    };

    $scope.studentUpperBound = function() {
        return moment().add(12, 'months').format("MMMM YYYY");
    };

    $scope.validFinancialAccount = function (source) {
        var valid = false;
        if( typeof source.assets !== "undefined" ) {
            for( var idx = 0; idx < source.assets.length; ++idx ) {
                valid |= (source.assets[idx].amount > 0);
            }
        }
        valid &= (source.name.length > 0);
        return valid;
    };

    $scope.housingHistoryLowerBound = function() {
        return moment().subtract(2, 'years').format("MMMM YYYY");
    };

    // Methods for past addresses
    // --------------------------
    $scope.addPastAddress = function(pastAddresses, event) {
        if( event ) {
            event.preventDefault();
        }
        var endsAt = moment().toDate();
        var startsAt = moment(endsAt).subtract(2, "years").toDate();
        if( pastAddresses.length > 0) {
            startsAt = moment(
                pastAddresses[pastAddresses.length - 1].ends_at.val).toDate();
        }
        pastAddresses.push({
            starts_at: {opened: false, val: startsAt},
            ends_at: {opened: false, val: endsAt},
            street_address: "",
            locality: "", region: "CA", postal_code: "", country: "US",
            monthly_rent: 0
        });
    };

    $scope.setMaritalStatus = function (event, applicant, status) {
        event.preventDefault();
        applicant.marital_status = status;
        $scope.gotoStep(event);
    };

    $scope.addFirstChild = function (event, children, node) {
        event.preventDefault();
        $scope.addChild(event, children);
        return $scope.showNode(event, node);
    };

    $scope.addChild = function (event, children) {
        event.preventDefault();
        var today = moment();
        children.push({full_name: "",
           relation_to_head: $scope.CHILD,
           date_of_birth: {
               // Implementation Note:
               // We use "0" instead of int(0) because the value is used
               // in a <select>.
               year: today.year(), month: "0", day: 1},
           full_time_student: false});
    };

    $scope.removeAtIndex = function (event, array, idx) {
        event.preventDefault();
        array.splice(idx, 1);
    };

    $scope.addSupportPayment = function(event, sources, options) {
        event.preventDefault();
        $scope.addSource(event, sources, options);
        sources[sources.length - 1]["incomes"] = [{
            category: "", period: $scope.MONTHLY,
            period_per_avg: 0, avg_per_year: 12,
            court_award: "", payer: "", collection: false, descr: ""
        }];
    };

    $scope.addOtherPayment = function(event, sources) {
        event.preventDefault();
        $scope.addSource(event, sources);
        sources[sources.length - 1]["incomes"] = [{
            category: "", period: $scope.MONTHLY,
            period_per_avg: 0, avg_per_year: 12
        }];
    };

    $scope.hasSourceSelected = function(source) {
        return ((typeof source.name !== "undefined"
                && source.name !== "")
          || (typeof source.pk !== "undefined"
                && source.pk !== ""
                && source.pk !== "add-source"));
    };

    $scope.hasSourcePosition = function(source) {
        return $scope.hasSourceSelected(source)
            && source.position && source.position !== "";
    };

    $scope.checkAddSource = function(source) {
        if( source.pk === "add-source" ) {
            window.location = settings.urls.add_source;
        } else {
            source.slug = settings.sources[source.pk].slug;
            source.position = settings.sources[source.pk].position;
            source.name = settings.sources[source.pk].name;
            source.street_address = settings.sources[source.pk].street_address;
            source.locality = settings.sources[source.pk].locality;
            source.region = settings.sources[source.pk].region;
            source.postal_code = settings.sources[source.pk].postal_code;
            source.country = settings.sources[source.pk].country;
            source.email = settings.sources[source.pk].email;
            source.phone = settings.sources[source.pk].phone;
        }
    };

    $scope.updateVerified = function(source) {
        if( $scope.hasImplicitPeriod(source) ) {
            for( var j = 0; j < source.incomes.length; ++j ) {
                source.incomes[j].period = $scope.OTHER;
                source.incomes[j].avg = $scope.OTHER;
            }
            source.avg_per_year = $scope.naturalAvgPerYear($scope.OTHER);
        }
    };

    $scope.hasVerificationSelected = function(source) {
        return ($scope.hasSourceSelected(source)
                && (typeof source.verified !== "undefined"
                    && source.verified !== ""));
    };

    $scope.addSource = function(event, sources, options) {
        event.preventDefault();
        sources.push($.extend({}, {name: "", incomes: []}, options));
        var self = $(event.currentTarget);
        var parent = self.parents(".content-inner");
        $timeout(function() {
            var bankUI = parent.find(".information").last();
            var focusUI = bankUI.find("[name='source-position']");
            if ( !focusUI ) focusUI = bankUI.find("[name='source-name']");
            focusUI.focus();
        });
        return false;
    };

    $scope.addSourceIncomes = function(event, sources, categories, options) {
        event.preventDefault();
        var source = sources[sources.length - 1];
        source["avg_per_year"] = categories.hasOwnProperty("regular") ? 52 : 0;
        for( var key in categories ) {
            if( categories.hasOwnProperty(key) ) {
                source["incomes"].push($.extend({}, {
                    category: key, amount: '', period: $scope.HOURLY,
                    avg: $scope.WEEKLY, period_per_avg: '', avg_per_year: 0,
                }, options));
            }
        }
        return false;
    };

    $scope.addSourceAssets = function(event, sources, categories, options) {
        event.preventDefault();
        var source = sources[sources.length - 1];
        source["assets"] = [];
        for( var key in categories ) {
            if( categories.hasOwnProperty(key) ) {
                source["assets"].push($.extend({}, {
                    category: key, amount: '', interest_rate: 0,
                }, options));
            }
        }
        return false;
    };

    $scope.cashValueOfProperty = function(property) {
        if( property.foreclosure ) {
            return 0;
        }
        if( property.sell_price > 0 ) {
            var first = 0;
            for( var i = 0; i < property.assets.length; ++i ) {
                first += property.assets[i].amount
                    * property.assets[i].interest_rate / 100;
            }
            var imputed = 0;
            if( first > 5000 ) {
                imputed = $scope.salesProceedsProperty(property) * 2 / 100;
            }
            return Math.max(first, imputed);
        }
        return property.amount - property.reverse_mortgage;
    };

    $scope.salesProceedsProperty = function(property) {
        if( property.foreclosure ) {
            return 0;
        }
        return property.sell_price
            - property.total_mortgage - property.sell_closing_cost;
    };

    $scope.incomeFromPropertyRental = function(property) {
        var cashValue = $scope.cashValueOfProperty(property);
        var monthlyIncome = (property.rent_collected - property.monthly_mortgage
            - property.maintenance);
        return Math.max(cashValue, monthlyIncome);
    };

    $scope.addPropertyAccount = function(event, property) {
        event.preventDefault();
        property.assets.push({
            category: $scope.BANK_CD, amount: 0, interest_rate: 0});
        return false;
    };

    // Methods to help with presentation
    // ---------------------------------
    $scope.first_name = function(full_name) {
        return full_name.split(" ")[0];
    };

    $scope.last_name = function(full_name) {
        return full_name.split(" ")[1];
    };

    $scope.birthDate = function(dateOfBirth) {
        return moment(new Date(
            dateOfBirth.year, parseInt(dateOfBirth.month), dateOfBirth.day));
    };

    $scope.age = function(dateOfBirth) {
        var now = moment();
        return now.diff($scope.birthDate(dateOfBirth), 'years');
    };

    $scope.bornSameYear = function(dateOfBirth) {
        var famousPeople = {
            1900: "Louis Armstrong",
            1901: "Walt Disney",
            1902: "Charles Lindbergh",
            1903: "George Orwell",
            1904: "Salvador Dali",
            1905: "Greta Garbo",
            1906: "Josephine Baker",
            1907: "John Wayne",
            1908: "Ian Fleming",
            1909: "Errol Flynn",
            1910: "Mother Teresa",
            1911: "Ronald Reagan",
            1912: "Alan Turing",
            1913: "Rosa Parks",
            1914: "Joe DiMaggio",
            1915: "Frank Sinatra",
            1916: "Kirk Douglas",
            1917: "Ella Fitzgerald",
            1918: "Nelson Mandela",
            1919: "Jackie Robinson",
            1920: "Yul Brynner",
            1921: "Charles Bronson",
            1922: "Jack Kerouac",
            1923: "Charlton Heston",
            1924: "Curtis W. Harris",
            1925: "Richard Burton",
            1926: "Marilyn Monroe",
            1927: "Cesar Chavez",
            1928: "Andy Warhol",
            1929: "Martin Luther King Jr.",
            1930: "Neil Armstrong",
            1931: "James Dean",
            1932: "Elizabeth Taylor",
            1933: "James Brown",
            1934: "Yuri Gagarin",
            1935: "Elvis Presley",
            1936: "John Madden",
            1937: "Morgan Freeman",
            1938: "Shirley Caesar",
            1939: "Tina Turner",
            1940: "Bruce Lee",
            1941: "Bernie Sanders",
            1942: "Muhammad Ali",
            1943: "Robert De Niro",
            1944: "George Lucas",
            1945: "Bob Marley",
            1946: "Donald Trump",
            1947: "Hillary Clinton",
            1948: "Samuel L. Jackson",
            1949: "Arsene Wenger",
            1950: "Stevie Wonder",
            1951: "Mark Harmon",
            1952: "Mr T.",
            1953: "Hulk Hogan",
            1954: "Jackie Chan",
            1955: "Bill Gates",
            1956: "David Copperfield",
            1957: "Bernie Mac",
            1958: "Michael Jackson",
            1959: "Simon Cowell",
            1960: "Diego Maradona",
            1961: "George Lopez",
            1962: "Demi Moore",
            1963: "Michael Jordan",
            1964: "Keanu Reeves",
            1965: "Chris Rock",
            1966: "Janey Jackson",
            1967: "Van Diesel",
            1968: "Will Smith",
            1969: "Jennifer Lopez",
            1970: "Mariah Carey",
            1971: "Snoop Dogg",
            1972: "Cameron Diaz",
            1973: "Larry Page",
            1974: "Leonardo DiCaprio",
            1975: "Angelina Jolie",
            1976: "Gabriel Iglesias",
            1977: "Shakira",
            1978: "Kobe Bryant",
            1979: "Adam Levine",
            1980: "Kim Kardashian",
            1981: "Beyonce Knowles",
            1982: "Prince William",
            1983: "Roman Atwood",
            1984: "LeBron James",
            1985: "Christiano Ronaldo",
            1986: "Drake",
            1987: "Lionel Messi",
            1988: "Rihanna",
            1989: "Taylor Swift",
            1990: "Petra Kvitova",
            1991: "Emma Roberts",
            1992: "Kate Upton",
            1993: "Ariana Grande",
            1994: "Justin Bieber",
            1995: "Claressa Shields",
            1996: "Abigail Breslin",
            1997: "Simone Biles",
            1998: "Guan Tianlang",
        };
        return famousPeople[dateOfBirth.year];
    };

    $scope.section8Hidden = true;
    $scope.askSection8 = function(event, student) {
        $scope.section8Hidden = false;
        showNode($event, '#student-section8')
    };

    $scope.activeNode = function(event, name, hidden) {
        for( var i = 0; i < hidden.length; ++i ) {
            $scope.hideNode(event, hidden[i]);
        }
        $scope.showNode(event, name);
    };

    $scope.hideNode = function(event, name) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".trigger");
        var node = parent.find(name).last();
        node.hide();
    };

    $scope.showNode = function(event, name) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".trigger");
        var node = parent.find(name).last();
        node.show();
    };

    // moving through the UI.
    $scope.addSupportPaymentData = function(event, property, account) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".information").first();
        parent.find(".other").show();
        return false;
    };

    $scope.showAllBanks = function(event) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".input-group");
        var typeahead = self.parents(".input-group").find("ul");
        typeahead.removeClass("ng-hide").addClass("test123");
        typeahead.append("<li>testing...</li>");
    };

    $scope.getBanks = function(val) {
        var banks = [{name: "Wells Fargo"}, {name: "Chase"}];
        var results = [];
        var query = val.toLowerCase();
        for( var i = 0; i < banks.length; ++i ) {
            if( banks[i].name.toLowerCase().indexOf(query) === 0 ) {
                results.push(banks[i]);
            }
        }
        return results;
    };

    $scope.addRealEstate = function(event, property) {
        event.preventDefault();
        $scope.gotoStep(event);
        return false;
    };

    $scope.addPropertySold = function(event, property) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents("#property-sold");
        var accountUI = parent.find("#proceeds-deposit");
        accountUI.show();
    };

    $scope.showPropertyCashValue = function(event, property) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".proceeds-information").first();
        parent.find(".other").show();
        return false;
    };

    $scope.addPropertyData = function(event, property, account) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".information").first();
        parent.find(".other").show();
        return false;
    };

    $scope.addEmployeeData = function(event) {
        event.preventDefault();
        var self = $(event.currentTarget);
        var parent = self.parents(".information");
        parent.find(".other").show();
        return false;
    };

    $scope.gotoStep = function(event, step) {
        if( typeof event !== "undefined" ) {
            event.preventDefault();
        }
        var next = step;
        if( typeof step === "undefined" ) {
            next = $(event.currentTarget).parents(".wizard-step").next();
        }
        var element = angular.element(next);
        var offsetTop = (typeof element.offset() !== "undefined") ? element.offset().top : 0;
        $('html, body').animate({scrollTop: offsetTop}, 500, function() {
           $(next).find("button,input,select").filter(":visible:first").focus();
        });
        return false;
    };

    $scope.completeApplication = function(postUrl, method) {
        var buttonElememt = angular.element('#fill-application-submit');
        var origText = null;
        if( buttonElememt ) {
            origText = buttonElememt.text();
            buttonElememt.html(
                "<i class=\"fa fa-spinner\"></i> Processing ...");
            buttonElememt.attr("disabled", "disabled");
        }
        var application = JSON.parse(JSON.stringify($scope.application));

        // children
        if( typeof application.children !== "undefined" ) {
            if( application.children.length === 0 ) {
                delete application.children.length;
            } else {
                for( var i = 0; i < application.children.length; ++i ) {
                    application.children[i].date_of_birth = $scope.birthDate(
                        application.children[i].date_of_birth);
                }
            }
        }

        for( var appIdx = 0; appIdx <
                 application.applicants.length; ++appIdx ) {
            var applicant = application.applicants[appIdx];

            // profile data
            if( typeof applicant.date_of_birth !== "undefined" ) {
                applicant.date_of_birth
                    = $scope.birthDate(applicant.date_of_birth);
            }
            if( typeof applicant.race !== "undefined" ) {
                if( applicant.race === "" ) {
                    delete applicant.race;
                } else {
                    applicant.race = parseInt(applicant.race);
                }
            }
            if( typeof applicant.ethnicity !== "undefined" ) {
                if( applicant.ethnicity === "" ) {
                    delete applicant.ethnicity;
                } else {
                    applicant.ethnicity = parseInt(applicant.ethnicity);
                }
            }
            if( typeof applicant.disabled !== "undefined" ) {
                if( applicant.disabled === "" ) {
                    delete applicant.disabled;
                } else {
                    applicant.disabled = parseInt(applicant.disabled);
                }
            }

            // past addresses
            if( typeof applicant.past_addresses !== "undefined" ) {
                for( var i = 0; i < applicant.past_addresses.length; ++i ) {
                    applicant.past_addresses[i].starts_at = moment(
                        applicant.past_addresses[i].starts_at.val).format(
                            "YYYY-MM-DDTHH:MM");
                    applicant.past_addresses[i].ends_at = moment(
                        applicant.past_addresses[i].ends_at.val).format(
                            "YYYY-MM-DDTHH:MM");
                }
            }

            // student status
            if( typeof applicant.student_status !== "undefined" ) {
                if( applicant.student_status.financial_aid.amount === 0 ) {
                    delete applicant.student_status.financial_aid;
                } else {
                    applicant['studentfinancialaid'] = {
                        'incomes': [{
                            'amount': Math.round(account.amount * 100),
                            'period_per_avg':
                                Math.round(account.period_per_avg * 100),
                            'avg_per_year':
                                Math.round(account.avg_per_year * 100)
                        }]
                    }
                }
                if( applicant.student_status.cost_of_tuition.amount === 0 ) {
                    delete applicant.student_status.cost_of_tuition;
                } else {
                    var account = applicant.student_status.cost_of_tuition;
                    account.amount = Math.round(account.amount * 100);
                    account.period_per_avg = Math.round(account.period_per_avg * 100);
                    account.avg_per_year = Math.round(account.avg_per_year * 100);
                }
            }

            // income and assets
            for( var idx = 0; idx < $scope.QUESTIONS.length; ++idx ) {
                if( applicant.hasOwnProperty($scope.QUESTIONS[idx]) ) {
                    var empty = true;
                    var question = applicant[$scope.QUESTIONS[idx]];
                    for( var i = 0; i < question.length; ++i ) {
                        var source = question[i];
                        if( source.incomes ) {
                            for( var j = 0; j < source.incomes.length; ++j ) {
                                var account = source.incomes[j];
                                if( !jQuery.isNumeric(account.amount) ) {
                                    account.amount = 0;
                                }
                                if( !jQuery.isNumeric(account.period_per_avg) ) {
                                    account.period_per_avg = 0;
                                }
                                if( account.amount != 0 ) {
                                    /* We use negative numbers to DELETE entries. */
                                    empty = false;
                                    account.verified = source.verified;
                                    account.starts_at = source.starts_at;
                                    account.ends_at = source.ends_at;
                                    account.amount = Math.round(
                                        account.amount * 100);
                                    account.period_per_avg = Math.round(
                                        account.period_per_avg * 100);
                                    if( typeof source.avg_per_year !== "undefined" ) {
                                        account.avg_per_year = Math.round(
                                            $scope.naturalAvgPerYear(account.period)
                                                * source.avg_per_year * 100
                                                / $scope.naturalAvgPerYear(source.incomes[0].period));
                                    } else {
                                        account.avg_per_year = Math.round(
                                            account.avg_per_year * 100);
                                    }
                                    if( $scope.notes ) {
                                        if( $scope.notes.text.length > 0 ) {
                                            account.descr = "" + $scope.notes.text;
                                        } else {
                                            account.descr = "";
                                        }
                                    }
                                    // extra information
                                    if( account.hasOwnProperty('cash_wages') ) {
                                        account.cash_wages = source.cash_wages;
                                    }
                                    if( account.hasOwnProperty('court_award') ) {
                                        account.court_award =
  (account.court_award === 'no') ? "no"
  : ((account.hasOwnProperty('collection') && account.collection) ?
       "partial" : "yes");
                                    }
                                }
                            }
                        }
                        if( source.assets ) {
                            for( var j = 0; j < source.assets.length; ++j ) {
                                var account = source.assets[j];
                                if( !jQuery.isNumeric(account.amount) ) {
                                    account.amount = 0;
                                }
                                if( account.amount != 0 ) {
                               /* We use negative numbers to DELETE entries. */
                                    empty = false;
                                    account.verified = source.verified;
                                    account.amount = Math.round(
                                        account.amount * 100);
                                    account.interest_rate = Math.round(
                                        account.interest_rate * 100);
                                    if( $scope.notes ) {
                                        if( $scope.notes.text.length > 0 ) {
                                            account.descr = "" + $scope.notes.text;
                                        } else {
                                            account.descr = "";
                                        }
                                    }
                                }
                            }
                        }
                    }
                    if( empty ) {
                        delete applicant[$scope.QUESTIONS[idx]];
                    }
                }
            }

            // Assets
            if( typeof applicant.properties !== "undefined" ) {
                for( var i = 0; i < applicant.properties.length; ++i ) {
                    var property = applicant.properties[i];
                    if( property.sell_price > 0 ) {
                        var descr = ("Sold real-estate on " + property.sell_at
                         + "for $" + property.sell_price
                         + "with $" + property.total_mortgage + " owed mortgage"
                         + " and $" + property.sell_closing_cost + " of closing"
                         + " cost.");
                        for( var j = 0; j < property.assets.length; ++j ) {
                            var account = property.assets[j];
                            descr += (" " + account.amount + " deposited in a "
                              + account.interest_rate + "% "
                              + $scope.BANK_CATEGORY[account.category]
                              + " at " + account.name + ".");
                        }
                        var category = $scope.NORMAL_SALE;
                        if( property.foreclosure ) {
                            category = $scope.FORECLOSURE;
                        } else if( property.short_sale ) {
                            category = $scope.SHORT_SALE;
                        }
                    } else {
                        var descr = property.descr;
                        if( property.reverse_mortgage > 0 ) {
                            descr = ("Balance of $" + property.reverse_mortgage
                             + "on a reverse mortgage for a property value of $"
                             + property.amount
                             + " (" + property.descr + ").");
                        }
                        if( property.rent_collected ) {
                            var descr = ("Real-estate rented for $"
                             + property.rent_collected + " monthly "
                             + "less a mortgage of $" + property.monthly_mortgage
                             + "and maintenace costs of $" + property.maintenance
                             + " (" + property.descr + ").");
                        }
                    }
                }
            }

            // assets: cash on hand
            if( typeof applicant.cash_on_hand !== "undefined" ) {
                if( applicant.cash_on_hand.amount == 0 ) {
                    delete applicant.cash_on_hand;
                } else {
                    applicant.cash_on_hand.amount = Math.round(
                        applicant.cash_on_hand.amount * 100);
                }
            }
        }
        // POST application
        if( typeof method === "undefined" ) {
            $http({
                method: 'POST',
                url: postUrl,
                headers: {'Accept': "text/html, application/json, text/plain, */*"},
                data: application
            }).then(function(resp){
                if( typeof resp.data.location !== "undefined" ) {
                    window.location = resp.data.location;
                } else {
                    document.open('text/html');
                    document.write(resp.data);
                    document.close();
                }
            }, function(resp) {
                if( buttonElememt ) {
                    buttonElememt.text(origText);
                    buttonElememt.removeAttr("disabled");
                }

                // Errors in the application cover.
                $scope.decorateWithErrors(resp);
            });
        } else {
            $http.put(postUrl, application).then(
                function(resp){ // success
                window.location = window.location.pathname.split('/').slice(0, -2).join('/') + '/';
            }, function(resp) { // error
                $scope.decorateWithErrors(resp);
            });
        }
    };

    $scope.deleteEntry = function(postUrl, method) {
        for( var idx = 0; idx < $scope.QUESTIONS.length; ++idx ) {
            if( $scope.activeApplicant.hasOwnProperty($scope.QUESTIONS[idx]) ) {
                var question = $scope.activeApplicant[$scope.QUESTIONS[idx]];
                for( var i = 0; i < question.length; ++i ) {
                    var source = question[i];
                    if( source.incomes ) {
                        for( var j = 0; j < source.incomes.length; ++j ) {
                            source.incomes[j].amount = -1;
                        }
                    }
                    if( source.assets ) {
                        for( var j = 0; j < source.assets.length; ++j ) {
                            source.assets[j].amount = -1;
                        }
                    }
                }
            }
        }
        $scope.completeApplication(postUrl, method);
    };

    $scope.decorateWithErrors = function(resp) {
        if( typeof resp.data !== "undefined" &&
            typeof resp.data.applicants !== "undefined" ) {
            for( var i = 0; i < resp.data.applicants.length; ++i ) {
                $scope.recursiveDecorateWithErrors(
                    angular.element("#applicant-" + i),
                    resp.data.applicants[i]);
            }
            showErrorMessages("<span style='margin-left:50px;'>We spotted" +
" some issues with the information you inputed. Please correct the fields" +
" marked in red and submit again. Thank you.</span>");
        } else if( resp.status != 500 ) {
            showErrorMessages(resp);
        } else {
            showErrorMessages("<span style='margin-left:50px;'>" +
" You stumble upon a major logic error on the site. We have been notified" +
" and have started working on fixing it. Please accept our apologies.</span>");
        }
    };

    $scope.recursiveDecorateWithErrors = function(root, errs) {
        for( var attr in errs ) {
            if( errs.hasOwnProperty(attr) ) {
                var msg = errs[attr];
                if( Array.isArray(msg) ) {
                    if( msg.length > 0 && typeof msg[0] === 'string' ) {
                        // Look for a global node first.
                        var elm = angular.element("#" + attr);
                        if( elm.length == 0 ) {
                            elm = root.find("[name$=\"" + attr + "\"]");
                        }
                        elm = elm.parents(".form-group");
                        elm.addClass("has-error");
                        elm.find(".help-block").text(msg);
                    } else {
                        for( var i = 0; i < msg.length; ++i ) {
                            var node = root.find("#" + attr + "-" + i);
                            $scope.recursiveDecorateWithErrors(node, msg[i]);
                        }
                    }
                } else {
                    var elm = root.find("#" + attr);
                    $scope.recursiveDecorateWithErrors(elm, msg);
                }
            }
        }
    };

    $scope.addApplicationTenant = function(event) {
        // Implementation Note:
        // We use "1" instead of int(1) because the value is used in a <select>.
        $scope.application.applicants.push({
            full_name: "",
            date_of_birth: {year: "", month: "0", day: 1},
            relation_to_head: $scope.HEAD_OF_HOUSEHOLD,
            marital_status: 0,
            ssn: "",
            race: "", // (1<<7) did not respond
            ethnicity: "",
            disabled: "",
            email: "",
            phone: "",
            past_addresses: [],
            student_status: {
                current: false, past: false, future: false,
                title_iv: false, job_training: false,
                has_children: false, foster_care: false,
                financial_aid: {amount: 0, period: $scope.MONTHLY},
                cost_of_tuition: {amount: 0, period: $scope.MONTHLY}},
            selfemployed: [],
            employee: [],
            // Benefits
            disability: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            publicassistance: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            socialsecurity: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            supplemental: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            unemployment: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            veteran: [{incomes:[{
                amount: '', period: $scope.MONTHLY, period_per_avg: 0,
                avg_per_year: 12}]}],
            support_payments: [],
            // Assets
            fiduciaries: [],
            properties: [{
                amount: 0, descr: "",
                rent_collected: 0, monthly_mortgage: 0, maintenance: 0,
                reverse_mortgage: 0,
                sell_at: {year: "", month: "1", day: 1},
                sell_price: 0, total_mortgage: 0, sell_closing_cost:0,
                foreclosure: false, short_sale: false,
                assets: []}],
            life_insurances: [],
            cash_on_hand:{
                amount: 0
            },
            others: []
        });

        var applicant = $scope.application.applicants[
            $scope.application.applicants.length - 1];
        if( $scope.application.applicants.length > 1 ) {
            applicant.relation_to_head = "";
        }
        if( applicant.past_addresses.length === 0 ) {
            $scope.addPastAddress(applicant.past_addresses);
        }
        $("#fill-application").modal('hide');
        var elmId = "#applicant-" + ($scope.application.applicants.length - 1) + " #fullname";
        $scope.waitForElement(event, elmId);
    };

    $scope.waitForElement = function(event, elmId) {
        if( angular.element(elmId).length > 0 ) {
            $scope.gotoStep(event, elmId);
        } else {
            $timeout(function() { $scope.waitForElement(event, elmId) }, 50);
        }
    };

    $scope.application = {
        slug: "",
        lihtc_property: settings.lihtcProperty,
        applicants: [],
        children: []
    };

    $scope.sources = settings.sources;
    if( !(typeof $scope.sources === "undefined") ) {
        for( var i = 0; i < $scope.sources.length; ++i ) {
            $scope.sources[i].pk = i;
        }
    }

    // Initialize with pre-loaded data in the HTML page.
    $scope.notes = null;
    if( !(typeof settings.application === "undefined") ) {
        $scope.notes = {text: ""};
        $scope.application = settings.application;
        for( var tenantIdx = 0;
             tenantIdx < (settings.application.applicants || []).length; ++tenantIdx ) {
        var applicant = $scope.application.applicants[tenantIdx];
        for( var idx = 0; idx < $scope.QUESTIONS.length; ++idx ) {
            if( applicant.hasOwnProperty($scope.QUESTIONS[idx]) ) {
                var question = applicant[$scope.QUESTIONS[idx]];
                for( var i = 0; i < question.length; ++i ) {
                    var source = question[i];
                    if( typeof source.starts_at !== "undefined" ) {
                        source.starts_at = new Date(source.starts_at);
                        var userTimezoneOffset =
                            source.starts_at.getTimezoneOffset() * 60000;
                        source.starts_at = new Date(source.starts_at.getTime()
                            + userTimezoneOffset);
                    } else {
                        source.starts_at = moment().startOf('year').toDate();
                    }
                    if( typeof source.ends_at !== "undefined" ) {
                        source.ends_at = new Date(source.ends_at);
                        var userTimezoneOffset =
                            source.ends_at.getTimezoneOffset() * 60000;
                        source.ends_at = new Date(source.ends_at.getTime()
                            + userTimezoneOffset);
                    } else {
                        source.ends_at = moment().toDate();
                    }
                    if( source.incomes ) {
                        if( source.incomes.length > 0) {
                            for( var j = 0; j < source.incomes.length; ++j ) {
                                var account = source.incomes[j];
                                account.amount /= 100.0;
                                account.period_per_avg /= 100.0;
                                account.avg_per_year /= 100.0;
                                if( account.descr ) {
                                    if( $scope.notes.text ) {
                                        $scope.notes.text += "\n";
                                    }
                                    $scope.notes.text += account.descr;
                                }
                            }
                            source.avg_per_year = source.incomes[0].avg_per_year;
                        } else {
                            source.avg_per_year = 52;
                        }
                    }
                    if( source.assets ) {
                        if( source.assets.length > 0 ) {
                            for( var j = 0; j < source.assets.length; ++j ) {
                                var account = source.assets[j];
                                account.amount /= 100.0;
                                account.interest_rate /= 100.0;
                                if( account.descr ) {
                                    if( $scope.notes.text ) {
                                        $scope.notes.text += "\n";
                                    }
                                    $scope.notes.text += account.descr;
                                }
                            }
                        }
                    }
                }
            }
        }
        if( typeof applicant.past_addresses !== "undefined" ) {
            for( var i = 0; i < applicant.past_addresses.length; ++i ) {
                applicant.past_addresses[i].starts_at = {
                    opened: false, val: applicant.past_addresses[i].starts_at};
                applicant.past_addresses[i].ends_at = {
                    opened: false, val: applicant.past_addresses[i].ends_at};
            }
        }
        $scope.activeApplicant = applicant;
        }
    } else {
        $scope.addApplicationTenant();
    }

    $scope.periodUpdated = function(benefits) {
        if( typeof benefits !== "undefined" ) {
            benefits.avg_per_year = $scope.naturalAvgPerYear(benefits.period);
        }
    };


    $scope.removeApplicationResident = function(application, resident) {
        $http.delete(settings.urls.api_application_resident).then(
            function(resp) {
                window.location = settings.urls.application.application_detail;
            },
            function(resp) {
                showErrorMessages(resp);
            });
    };

    $scope.loadDocuments = function() {
        $http.get(settings.urls.api_document_upload
        ).then(function(resp) {
            $scope.application.docs = resp.data.results;
        }, function(resp) {
            showErrorMessages(resp);
        });
    }

    if( settings.urls && settings.urls.api_document_upload ) {
        // Loads list of supporting documents
        if( settings.urls.api_credentials ) {
            $http.get(settings.urls.api_credentials
            ).then(function(resp) {
                $scope.loadDocuments();
            }, function(resp) {
                showErrorMessages(resp);
            });
        } else {
            $scope.loadDocuments();
        }
    }

}]);


tcappControllers.controller("tcappIncomeCtrl",
    ["$scope", "$http", function($scope, $http) {
    "use strict";

    $scope.incomes = [{source: "", monthly_gross_income: ""}];

    $scope.onClickAddIncome = function($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.incomes.push({source: "", monthly_gross_income: ""});
    };

}]);

// List of tenant applications
// (code copy/pasted from djaodjin-saas-angular.js:itemsListCtrl)
tcappControllers.controller("tcappApplicationListCtrl",
    ["$scope", "$attrs", "$http", "$timeout", "settings",
     function($scope, $attrs, $http, $timeout, settings) {
    "use strict";
    $scope.items = {};
    $scope.totalItems = 0;
    $scope.apiUrl = $attrs.apiUrl ? $attrs.apiUrl : settings.urls.api_items;
    $scope.autoload = $attrs.autoload ? $attrs.autoload : settings.autoload;

    $scope.resetDefaults = function(overrides) {
        $scope.dir = {};
        var opts = {};
        if( settings.sortByField ) {
            opts['o'] = settings.sortByField;
            opts['ot'] = settings.sortDirection || "desc";
            $scope.dir[settings.sortByField] = opts['ot'];
        } else {
            opts['o'] = 'created_at';
            opts['ot'] = "desc";
            $scope.dir[opts['o']] = opts['ot'];
        }
        if( settings.date_range ) {
            if( settings.date_range.start_at ) {
                opts['start_at'] = moment(settings.date_range.start_at).toDate();
            }
            if( settings.date_range.ends_at ) {
                opts['ends_at'] = moment(settings.date_range.ends_at).toDate()
            }
        }
        $scope.filterExpr = "";
        $scope.itemsPerPage = settings.itemsPerPage; // Must match server-side
        $scope.maxSize = 5;               // Total number of direct pages link
        $scope.currentPage = 1;
        // currentPage will be saturated at maxSize when maxSize is defined.
        $scope.formats = ["dd-MMMM-yyyy", "yyyy/MM/dd",
            "dd.MM.yyyy", "shortDate"];
        $scope.format = $scope.formats[0];
        $scope.opened = { "start_at": false, "ends_at": false };
        if( typeof overrides === "undefined" ) {
            overrides = {};
        }
        $scope.params = angular.merge({}, opts, overrides);
    };

    $scope.resetDefaults();

    // calendar for start_at and ends_at
    $scope.open = function($event, date_at) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.opened[date_at] = true;
    };

    // Generate a relative date for an instance with a ``created_at`` field.
    $scope.relativeDate = function(at_time) {
        var cutOff = new Date();
        if( $scope.params.ends_at ) {
            cutOff = new Date($scope.params.ends_at);
        }
        var dateTime = new Date(at_time);
        if( dateTime <= cutOff ) {
            return moment.duration(cutOff - dateTime).humanize() + " ago";
        } else {
            return moment.duration(dateTime - cutOff).humanize() + " left";
        }
    };

    $scope.$watch("params", function(newVal, oldVal, scope) {
        var updated = (newVal.o !== oldVal.o || newVal.ot !== oldVal.ot
            || newVal.q !== oldVal.q || newVal.page !== oldVal.page );
        if( (typeof newVal.start_at !== "undefined")
            && (typeof newVal.ends_at !== "undefined")
            && (typeof oldVal.start_at !== "undefined")
            && (typeof oldVal.ends_at !== "undefined") ) {
            /* Implementation Note:
               The Date objects can be compared using the >, <, <=
               or >= operators. The ==, !=, ===, and !== operators require
               you to use date.getTime(). Don't ask. */
            if( newVal.start_at.getTime() !== oldVal.start_at.getTime()
                && newVal.ends_at.getTime() === oldVal.ends_at.getTime() ) {
                updated = true;
                if( $scope.params.ends_at < newVal.start_at ) {
                    $scope.params.ends_at = newVal.start_at;
                }
            } else if( newVal.start_at.getTime() === oldVal.start_at.getTime()
                       && newVal.ends_at.getTime() !== oldVal.ends_at.getTime() ) {
                updated = true;
                if( $scope.params.start_at > newVal.ends_at ) {
                    $scope.params.start_at = newVal.ends_at;
                }
            }
        }

        if( updated ) {
            $scope.refresh();
        }
    }, true);

    $scope.filterList = function(regex) {
        if( regex ) {
            if ("page" in $scope.params){
                delete $scope.params.page;
            }
            $scope.params.q = regex;
        } else {
            delete $scope.params.q;
        }
    };

    $scope.pageChanged = function() {
        if( $scope.currentPage > 1 ) {
            $scope.params.page = $scope.currentPage;
        } else {
            delete $scope.params.page;
        }
    };

    $scope.sortBy = function(fieldName) {
        if( $scope.dir[fieldName] == "asc" ) {
            $scope.dir = {};
            $scope.dir[fieldName] = "desc";
        } else {
            $scope.dir = {};
            $scope.dir[fieldName] = "asc";
        }
        $scope.params.o = fieldName;
        $scope.params.ot = $scope.dir[fieldName];
        $scope.currentPage = 1;
        // pageChanged only called on click?
        delete $scope.params.page;
    };

    $scope.refresh = function() {
        $http.get($scope.apiUrl,
            {params: $scope.params}).then(
            function(resp) {
                // We cannot watch items.count otherwise things start
                // to snowball. We must update totalItems only when it truly
                // changed.
                if( resp.data.count != $scope.totalItems ) {
                    $scope.totalItems = resp.data.count;
                }
                $scope.items = resp.data;
                $scope.items.$resolved = true;
            }, function(resp) {
                $scope.items = {};
                $scope.items.$resolved = false;
                showErrorMessages(resp);
                $http.get($scope.apiUrl,
                    {params: angular.merge({force: 1}, $scope.params)}).then(
                function success(resp) {
                    // ``force`` load will not call the processor backend
                    // for reconciliation.
                    if( resp.data.count != $scope.totalItems ) {
                        $scope.totalItems = resp.data.count;
                    }
                    $scope.items = resp.data;
                    $scope.items.$resolved = true;
                });
            });
    };

    $scope.save = function(application) {
        $http.put($scope.apiUrl + '/' + application.slug, application,
            function(data) { //success
                showMessages(data);
            },
            function(resp) { // error
                showErrorMessages(resp);
            });
    };

    // Update of the application status propagates through the REST API.
    $scope.updateStatus = function(application) {
        $scope.save(application);
    };

    if( $scope.autoload ) {
        $scope.refresh();
    }
}]);
