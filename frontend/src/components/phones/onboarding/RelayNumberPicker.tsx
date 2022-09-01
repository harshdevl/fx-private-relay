import {
  ChangeEventHandler,
  FormEventHandler,
  MouseEventHandler,
  useState,
} from "react";
import { useLocalization } from "@fluent/react";
import styles from "./RelayNumberPicker.module.scss";
import FlagUS from "./images/flag-usa.svg";
import EnteryVerifyCodeSuccess from "./images/verify-code-success.svg";
import { Button } from "../../Button";
import {
  RelayNumberSuggestion,
  useRelayNumber,
  useRelayNumberSuggestions,
  search,
} from "../../../hooks/api/relayNumber";
import { formatPhone } from "../../../functions/formatPhone";
import { RefreshIcon } from "../../Icons";

type RelayNumberPickerProps = {
  onComplete: () => void;
};
export const RelayNumberPicker = (props: RelayNumberPickerProps) => {
  const [hasStarted, setHasStarted] = useState(false);
  const relayNumberData = useRelayNumber();
  const relayNumberSuggestionsData = useRelayNumberSuggestions();

  if (!hasStarted) {
    return <RelayNumberIntro onStart={() => setHasStarted(true)} />;
  }

  if (!relayNumberData.data || relayNumberData.data.length === 0) {
    return (
      <RelayNumberSelection
        registerRelayNumber={(number) =>
          relayNumberData.registerRelayNumber(number)
        }
        search={(query) => search(query)}
      />
    );
  }

  return <RelayNumberConfirmation onComplete={props.onComplete} />;
};

type RelayNumberIntroProps = {
  onStart: () => void;
};
const RelayNumberIntro = (props: RelayNumberIntroProps) => {
  const { l10n } = useLocalization();

  return (
    <div
      className={`${styles.step}  ${styles["step-input-verificiation-code"]} `}
    >
      <div className={`${styles.lead}  ${styles["is-success"]} `}>
        <div
          className={`${styles["step-input-verificiation-code-lead-success"]} `}
        >
          {/* Success state */}
          <img src={EnteryVerifyCodeSuccess.src} alt="" width={170} />
          <h2 className={`${styles["is-success"]} `}>
            {l10n.getString("phone-onboarding-step3-code-success-title")}
          </h2>
          <p>{l10n.getString("phone-onboarding-step3-code-success-body")}</p>
        </div>
      </div>
      {/* Add error class of `mzp-is-error` */}

      {/* TODO: Add logic to display success message */}

      <div className={`${styles["step-input-verificiation-code-success"]} `}>
        <h3>
          {l10n.getString("phone-onboarding-step3-code-success-subhead-title")}
        </h3>
        <p>
          {l10n.getString("phone-onboarding-step3-code-success-subhead-body")}
        </p>
        <Button onClick={() => props.onStart()} className={styles.button}>
          {l10n.getString("phone-onboarding-step3-code-success-cta")}
        </Button>
      </div>
    </div>
  );
};

type RelayNumberSelectionProps = {
  registerRelayNumber: (phoneNumber: string) => Promise<Response>;
  search: (search: string) => Promise<RelayNumberSuggestion[] | undefined>;
};
const RelayNumberSelection = (props: RelayNumberSelectionProps) => {
  const { l10n } = useLocalization();
  const relayNumberSuggestionsData = useRelayNumberSuggestions();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [relayNumberIndex, setRelayNumberIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [relayNumberSuggestions, setRelayNumberSuggestions] = useState<
    string[]
  >([]);

  if (relayNumberSuggestionsData.data && relayNumberSuggestions.length === 0) {
    setRelayNumberSuggestions(
      [
        ...relayNumberSuggestionsData.data.same_area_options,
        ...relayNumberSuggestionsData.data.other_areas_options,
        ...relayNumberSuggestionsData.data.same_prefix_options,
      ].map((suggestion) => suggestion.phone_number)
    );
  }

  const onRelayNumberChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    setPhoneNumber(event.target.value);
  };

  const onSearchChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    setSearchValue(event.target.value);
  };

  const onSubmitRelayNumber: FormEventHandler = (event) => {
    event.preventDefault();
    props.registerRelayNumber(phoneNumber);
  };

  const onSubmitSearch: FormEventHandler = async (event) => {
    event.preventDefault();

    // return early if search is currently taking place
    if (isSearching) return;

    // set search to true as we begin searching
    setIsSearching(true);

    const data = await props.search(searchValue);

    if (data && data?.length !== 0) {
      // add new relay number suggestions
      setRelayNumberSuggestions(
        data.map((suggestion) => suggestion.phone_number)
      );

      // reset relay number index
      setRelayNumberIndex(0);
    }

    // set search state to false
    setIsSearching(false);
  };

  const loadingState = !relayNumberSuggestionsData.data ? (
    <div className={`${styles["step-select-phone-number-mask-loading"]} `}>
      <div className={styles.loading} />
      <p>{l10n.getString("phone-onboarding-step3-loading")}</p>
    </div>
  ) : null;

  const getRelayNumberOptions: MouseEventHandler<HTMLButtonElement> = () => {
    const newRelayNumberIndex = relayNumberIndex + 3;

    // if we have reached the end of the list, reset to the beginning
    setRelayNumberIndex(
      newRelayNumberIndex >= relayNumberSuggestions.length
        ? 0
        : newRelayNumberIndex
    );
  };

  const suggestedNumberRadioInputs = relayNumberSuggestions
    .slice(relayNumberIndex, relayNumberIndex + 3)
    .map((suggestion, i) => {
      return (
        <div key={suggestion}>
          <input
            onChange={onRelayNumberChange}
            type="radio"
            name="phoneNumberMask"
            id={`number${i}`}
            value={suggestion}
            autoFocus={i === 0}
          />
          <label htmlFor={`number${i}`}>{formatPhone(suggestion)}</label>
        </div>
      );
    });

  const form = !relayNumberSuggestionsData.data ? null : (
    <div className={`${styles["step-select-phone-number-mask"]} `}>
      <div className={styles.lead}>
        <span>{l10n.getString("phone-onboarding-step4-country")}</span>
      </div>

      <form onSubmit={onSubmitSearch} className={styles.form}>
        <input
          className={styles.search}
          onChange={onSearchChange}
          placeholder={l10n.getString("phone-onboarding-step4-input-search")}
          type="search"
        />
      </form>

      <form onSubmit={onSubmitRelayNumber} className={styles.form}>
        <p className={styles.paragraph}>
          {l10n.getString("phone-onboarding-step4-body")}
        </p>

        <div className={`${styles["step-select-relay-numbers-radio-group"]} `}>
          {suggestedNumberRadioInputs}
        </div>

        <Button
          onClick={getRelayNumberOptions}
          className={`styles.button ${styles["show-more-options"]}`}
          type="button"
          variant="secondary"
        >
          <RefreshIcon alt="" />
          {l10n.getString("phone-onboarding-step4-button-more-options")}
        </Button>

        <p className={styles.paragraph}>
          {l10n.getString("phone-onboarding-step4-sub-body")}
        </p>

        {/* TODO: Add error class to input field */}
        <Button className={styles.button} type="submit">
          {l10n.getString(
            "phone-onboarding-step4-button-register-phone-number"
          )}
        </Button>
      </form>
    </div>
  );

  return (
    <div className={`${styles.step}`}>
      {/* TODO: Add logic to show this instead of step-select-phone-number-mask when loading */}
      {loadingState}
      {form}
    </div>
  );
};
type RelayNumberConfirmationProps = {
  onComplete: () => void;
};
const RelayNumberConfirmation = (props: RelayNumberConfirmationProps) => {
  const { l10n } = useLocalization();

  return (
    <div
      className={`${styles.step}  ${styles["step-input-verificiation-code"]} `}
    >
      <div className={`${styles.lead}  ${styles["is-success"]} `}>
        <div
          className={`${styles["step-input-verificiation-code-lead-success"]} `}
        >
          {/* Success state */}
          <img src={EnteryVerifyCodeSuccess.src} alt="" width={170} />
          <h2 className={`${styles["is-success"]} `}>
            {l10n.getString("phone-onboarding-step4-code-success-title")}
          </h2>
          <p>{l10n.getString("phone-onboarding-step4-code-success-body")}</p>
        </div>
      </div>
      {/* Add error class of `mzp-is-error` */}

      {/* TODO: Add logic to display success message */}

      <div className={`${styles["step-input-verificiation-code-success"]} `}>
        <h3>
          {l10n.getString("phone-onboarding-step4-code-success-subhead-title")}
        </h3>
        <p>
          {l10n.getString(
            "phone-onboarding-step4-code-success-subhead-body-p1"
          )}
        </p>
        <p>
          {l10n.getString(
            "phone-onboarding-step4-code-success-subhead-body-p2"
          )}
        </p>
        <Button onClick={() => props.onComplete()} className={styles.button}>
          {l10n.getString("phone-onboarding-step4-code-success-cta")}
        </Button>
      </div>
    </div>
  );
};
